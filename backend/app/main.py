import json
import os
import asyncio
import httpx
from typing import AsyncGenerator

from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler

from app.llm import OllamaClient
from app.model_routing import select_model
from app.models import CommandRequest
from app.tools import ToolRegistry
from app.executor import while_connected
from app.launch_runtime import BudgetedProvider
from app.operator import run_operator
from app.file_tools import register as register_files
from app.plugins import load_skills
from app.task_state import TaskState, Limits
from app.task_store import TaskStore
from app.window_observer import register as register_windows
from app.process_tools import register as register_process
from app.version import RUNTIME_VERSION
from app.computer_tools import register as register_computer
from app.provider_settings import ProviderSettings, CloudClient, PRESETS

app = FastAPI(title='Wingent', version='0.1.0')


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    if request.url.path.startswith('/api/settings'):
        return JSONResponse(status_code=422, content={'detail': 'Invalid settings. Check provider, model, HTTPS endpoint and API key.'})
    return await request_validation_exception_handler(request, exc)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://localhost:5173',
        'http://127.0.0.1:5173',
        'http://localhost:3000',
        'tauri://localhost',
        'http://tauri.localhost',
        'https://tauri.localhost',
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
registry = ToolRegistry()
register_files(registry)
register_windows(registry)
# One observation/input protocol in production. Legacy desktop/screen adapters
# use incompatible target IDs and grants and must not compete with this session.
register_computer(registry)
register_process(registry)
# Production UI tasks use observed Windows input, not direct app/browser launches.
# Keep the legacy modules available for compatibility tests, not model dispatch.
for launch_tool in ('open_application', 'open_url', 'search_web', 'open_folder'):
    registry.tools.pop(launch_tool, None)
loaded_skills = load_skills(registry, [name.strip() for name in os.getenv('WINGENT_SKILLS', '').split(',') if name.strip()])
task_store = TaskStore()
provider_settings = None


def make_provider(goal=''):
    settings = provider_settings
    if settings and settings.provider == 'cloud':
        return CloudClient(settings)
    return OllamaClient(model=settings.model if settings else select_model(goal))


@app.get('/api/settings')
def get_settings():
    return (provider_settings or ProviderSettings(model=select_model(''))).public()


@app.get('/api/provider-presets')
def provider_presets():
    return PRESETS


def resolve_settings(settings: ProviderSettings, request: Request):
    origin = request.headers.get('origin')
    if origin and origin not in {'http://localhost:5173', 'http://127.0.0.1:5173', 'tauri://localhost',
                                 'http://tauri.localhost', 'https://tauri.localhost'}:
        raise HTTPException(status_code=403, detail='Settings require the Wingent application origin.')
    if settings.provider == 'cloud' and not settings.api_key.get_secret_value().strip():
        previous = provider_settings
        if (previous and previous.provider == 'cloud' and previous.service == settings.service
                and previous.endpoint == settings.endpoint and previous.api_key.get_secret_value()):
            settings = settings.model_copy(update={'api_key': previous.api_key})
        else:
            raise HTTPException(status_code=422, detail='Enter an API key for this provider.')
    return settings.model_copy(deep=True)


@app.post('/api/settings')
def set_settings(settings: ProviderSettings, request: Request):
    global provider_settings
    provider_settings = resolve_settings(settings, request)
    return provider_settings.public()


@app.post('/api/settings/test')
async def test_settings(settings: ProviderSettings, request: Request, vision: bool = False):
    settings = resolve_settings(settings, request)
    try:
        async with asyncio.timeout(60 if vision else 20):
            if vision:
                # Synthetic pixels only: never capture/send the user's desktop.
                import secrets
                import struct
                import zlib
                color = secrets.choice(['red', 'green', 'blue'])
                rgb = {'red': b'\xff\x00\x00', 'green': b'\x00\x80\x00', 'blue': b'\x00\x00\xff'}[color]
                def chunk(kind, data):
                    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
                pixels = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 128, 128, 8, 2, 0, 0, 0))
                pixels += chunk(b'IDAT', zlib.compress((b'\0' + rgb * 128) * 128)) + chunk(b'IEND', b'')
                provider = (OllamaClient(model=settings.model) if settings.provider == 'local' else
                            CloudClient(settings.model_copy(update={'share_screenshots': True})))
                raw = await provider.structured_images('What solid color is the image: red, green or blue?',
                    'Report the image color in JSON. Do not guess without seeing the image.',
                    {'type': 'object', 'properties': {'color': {'type': 'string'}}, 'required': ['color']},
                    [pixels])
                ready = str(json.loads(raw).get('color', '')).strip().lower() == color
                return {'ready': ready, 'message': 'Vision test passed: synthetic image recognized. Desktop operation still needs testing.' if ready else 'Vision test failed: image color was not recognized.'}
            if settings.provider == 'local':
                return await OllamaClient(model=settings.model).availability()
            raw = await CloudClient(settings).structured('Return {"ok":true}.', 'Connection test. Return only JSON.',
                {'type': 'object', 'properties': {'ok': {'type': 'boolean'}}, 'required': ['ok'], 'additionalProperties': False})
            if json.loads(raw).get('ok') is not True:
                raise ValueError('Unexpected model response.')
        return {'ready': True, 'message': 'Connected. API key and selected model work. Vision was not tested.'}
    except (TimeoutError, httpx.TimeoutException):
        return {'ready': False, 'message': 'Connection test timed out. Check provider status and try again.'}
    except httpx.RequestError:
        return {'ready': False, 'message': 'Could not reach the provider. Check your network and endpoint.'}
    except RuntimeError as exc:
        return {'ready': False, 'message': str(exc)}
    except (ValueError, TypeError, AttributeError):
        return {'ready': False, 'message': 'Provider responded, but did not return the expected JSON. Check model compatibility.'}


def sse_event(event: str, payload: dict[str, object]) -> str:
    return f'event: {event}\ndata: {json.dumps(payload)}\n\n'


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok', 'service': 'wingent', 'runtime': RUNTIME_VERSION,
            'instance_id': os.getenv('WINGENT_INSTANCE_ID', '')}


class ApprovalResponse(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    token: str = Field(min_length=1, max_length=128)
    approve: bool


@app.post('/api/approvals/{approval_id}')
async def respond_to_approval(approval_id: str, response: ApprovalResponse):
    try:
        registry.approvals.respond(approval_id, response.token, response.approve)
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {'accepted': True}


@app.get('/api/capabilities')
def capabilities():
    return {'tools': registry.manifest(), 'loaded_skills': loaded_skills, 'capabilities': [
        {'name': c.name, 'available': c.available, 'guidance': c.guidance} for c in registry.capabilities.values()]}


@app.get('/api/model-status')
async def model_status():
    return await make_provider().availability()


@app.post('/api/command')
async def command(request: Request, command_request: CommandRequest) -> StreamingResponse:
    prompt = command_request.prompt.strip()
    resuming = command_request.resume_task_id is not None
    if resuming:
        try:
            pending_state = task_store.peek(command_request.resume_task_id)
        except KeyError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        resume_model = make_provider(pending_state.goal)
        available = await resume_model.is_available()
        if not available:
            message = (resume_model.last_availability or {}).get('message', 'Ollama is unavailable.')
            raise HTTPException(status_code=503, detail=message + ' The task remains resumable.')
        try:
            state = task_store.take(command_request.resume_task_id)
            state.resume(prompt)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    else:
        state = TaskState(goal=prompt, criteria=[prompt], limits=Limits(model_calls=12, seconds=360.0, operation_seconds=120.0))

    async def event_stream() -> AsyncGenerator[str, None]:
        yield sse_event('status', {'stage': 'planning', 'message': 'Planning request'})

        if await request.is_disconnected():
            return

        llm = BudgetedProvider(make_provider(state.goal), state)
        available = await while_connected(llm.is_available(), request.is_disconnected)
        if not available:
            diagnostic = llm.provider.last_availability or {
                'code': 'ollama_unavailable', 'message': f'Ollama model "{llm.provider.model}" is unavailable. Start Ollama and retry.'}
            yield sse_event(
                'error',
                {'message': diagnostic['message'], 'code': diagnostic['code']},
            )
            return

        async for event, payload in run_operator(registry, state, llm, request.is_disconnected,
                                                  review_actions=command_request.review_actions):
            if event == 'clarification' and payload.get('resume_task_id'):
                task_store.put(state)
            yield sse_event(event, payload)

    return StreamingResponse(event_stream(), media_type='text/event-stream')
