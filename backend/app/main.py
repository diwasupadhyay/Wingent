import asyncio
import json
import os
from typing import AsyncGenerator

from fastapi import FastAPI, Request
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
from app.planner import plan_request, compile_plan
from app.executor import execute_plan, while_connected
from app.folders import KNOWN_FOLDERS

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


def sse_event(event: str, payload: dict[str, object]) -> str:
    return f'event: {event}\ndata: {json.dumps(payload)}\n\n'


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok', 'service': 'wingent'}


@app.post('/api/command')
async def command(request: Request, command_request: CommandRequest) -> StreamingResponse:
    prompt = command_request.prompt.strip()

    async def event_stream() -> AsyncGenerator[str, None]:
        yield sse_event('status', {'stage': 'planning', 'message': 'Planning request'})

        if await request.is_disconnected():
            return

        if requests_unsupported_browser_automation(prompt):
            yield sse_event(
                'error',
                {
                    'message': (
                        'I can launch Chrome and open a site, but selecting a browser profile '
                        'requires browser automation, which is not enabled yet.'
                    ),
                    'code': 'unsupported_browser_automation',
                },
            )
            return

        llm = OllamaClient(
            base_url=os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434'),
            model=select_model(prompt),
        )
        actions = detect_deterministic_tools(prompt)
        if actions:
            async for event, payload in execute_plan(actions, registry, request.is_disconnected):
                yield sse_event(event, payload)
            return
        available = await while_connected(llm.is_available(), request.is_disconnected)
        if not available:
            yield sse_event(
                'error',
                {'message': 'Ollama is not available. Start the local model server or install a compatible model.'},
            )
            return

        yield sse_event('status', {'stage': 'planning', 'message': 'Interpreting your request with the local model'})
        try:
            plan = await while_connected(plan_request(prompt, llm), request.is_disconnected)
            if plan.disposition == 'clarify':
                yield sse_event('clarification', {'text': plan.message + ' No actions were taken. Please submit the full request with any missing details.'})
                return
            if plan.disposition == 'execute':
                # A generated path must be grounded in the user's text, never invented.
                for step in plan.steps:
                    if step.action == 'open_folder' and step.target.lower() not in {*KNOWN_FOLDERS, 'home'}:
                        if step.target.casefold() not in prompt.casefold():
                            raise ValueError('Please include the exact folder path in your request.')
                async for event, payload in execute_plan(compile_plan(plan), registry, request.is_disconnected):
                    yield sse_event(event, payload)
                return
        except asyncio.CancelledError:
            return
        except Exception as exc:
            yield sse_event('error', {'message': f'Could not create a valid plan: {exc or "local model timed out"}. No actions were taken.', 'code': 'planning_failed'})
            return

        yield sse_event('status', {'stage': 'streaming', 'message': 'Calling local model'})

        try:
            full = []
            async for text in llm.stream(prompt):
                if await request.is_disconnected():
                    return
                full.append(text)
                yield sse_event('delta', {'text': text})
        except asyncio.CancelledError:
            return
        except Exception as exc:  # pragma: no cover - defensive path
            yield sse_event('error', {'message': str(exc)})
            return

        result = ''.join(full).strip()
        if not result:
            yield sse_event('error', {'message': 'The local model returned no response. Try again or check the selected model.'})
            return
        yield sse_event('final', {'text': result})

    return StreamingResponse(event_stream(), media_type='text/event-stream')
