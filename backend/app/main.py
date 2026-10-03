import json
import os
from typing import AsyncGenerator

from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.llm import OllamaClient
from app.model_routing import select_model
from app.models import CommandRequest
from app.routing import (
    detect_deterministic_tools,
    requests_unsupported_browser_automation,
)
from app.tools import ToolRegistry
from app.executor import execute_plan, while_connected
from app.launch_runtime import BudgetedProvider
from app.operator import run_operator
from app.file_tools import register as register_files
from app.plugins import load_skills
from app.task_state import TaskState, Limits
from app.task_store import TaskStore
from app.browser_tools import register as register_browser
from app.window_observer import register as register_windows
from app.desktop_tools import register as register_desktop
from app.process_tools import register as register_process
from app.application_tools import register as register_applications
from app.screen_tools import register as register_screen
from app.version import RUNTIME_VERSION

app = FastAPI(title='Wingent', version='0.1.0')
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
desktop_session = register_desktop(registry)
register_screen(registry, desktop_session)
register_process(registry)
register_applications(registry)
register_browser(registry)
loaded_skills = load_skills(registry, [name.strip() for name in os.getenv('WINGENT_SKILLS', '').split(',') if name.strip()])
task_store = TaskStore()


def sse_event(event: str, payload: dict[str, object]) -> str:
    return f'event: {event}\ndata: {json.dumps(payload)}\n\n'


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok', 'service': 'wingent', 'runtime': RUNTIME_VERSION}


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


@app.post('/api/command')
async def command(request: Request, command_request: CommandRequest) -> StreamingResponse:
    prompt = command_request.prompt.strip()
    resuming = command_request.resume_task_id is not None
    if resuming:
        available = await OllamaClient(
            base_url=os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434'),
            model=select_model(prompt),
        ).is_available()
        if not available:
            raise HTTPException(status_code=503, detail='Ollama is unavailable. The task remains resumable.')
        try:
            state = task_store.take(command_request.resume_task_id)
            state.resume(prompt)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    else:
        state = TaskState(goal=prompt, criteria=[prompt], limits=Limits(model_calls=12, seconds=180.0))

    async def event_stream() -> AsyncGenerator[str, None]:
        yield sse_event('status', {'stage': 'planning', 'message': 'Planning request'})

        if await request.is_disconnected():
            return

        llm = BudgetedProvider(OllamaClient(
            base_url=os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434'),
            model=select_model(state.goal),
        ), state)
        actions = [] if resuming else detect_deterministic_tools(prompt)
        if actions:
            async for event, payload in execute_plan(actions, registry, request.is_disconnected, state=state, review_actions=command_request.review_actions):
                yield sse_event(event, payload)
            return
        available = await while_connected(llm.is_available(), request.is_disconnected)
        if not available:
            yield sse_event(
                'error',
                {'message': 'Ollama or the selected local model is unavailable. Start Ollama or install/configure the model.'},
            )
            return

        async for event, payload in run_operator(registry, state, llm, request.is_disconnected,
                                                  review_actions=command_request.review_actions):
            if event == 'clarification' and payload.get('resume_task_id'):
                task_store.put(state)
            yield sse_event(event, payload)

    return StreamingResponse(event_stream(), media_type='text/event-stream')
