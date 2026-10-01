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
    looks_like_action_request,
    requests_unsupported_browser_automation,
)
from app.tools import ToolRegistry

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

        deterministic_actions = detect_deterministic_tools(prompt)
        if not deterministic_actions and looks_like_action_request(prompt):
            yield sse_event(
                'error',
                {
                    'message': (
                        'Please specify the action after opening the browser. For example: '
                        '"open Chrome and search GitHub" or "open Chrome and open github.com". '
                        'I can open apps and sites or search; reading pages and clicking controls are not available yet. '
                        'No actions were taken.'
                    ),
                    'code': 'unsupported_action',
                },
            )
            return
        if deterministic_actions:
            results: list[dict[str, object]] = []
            for index, (tool_name, params) in enumerate(deterministic_actions, start=1):
                if await request.is_disconnected():
                    return
                tool = registry.get_tool(tool_name)
                if tool is None:
                    yield sse_event('error', {'message': 'No matching tool is available.'})
                    return

                yield sse_event(
                    'status',
                    {
                        'stage': 'tool_running',
                        'message': f'Opening {params.get("url") or params.get("application")} ({index}/{len(deterministic_actions)})',
                    },
                )
                try:
                    result = registry.execute(tool_name, params)
                except PermissionError as exc:
                    yield sse_event('error', {'message': str(exc), 'permission': 'confirmation_required'})
                    return
                except Exception as exc:  # pragma: no cover - defensive path
                    yield sse_event('error', {'message': str(exc)})
                    return

                results.append(result)

            summary = ' and '.join(
                str(item.get('url') or item.get('application') or item.get('action', 'tool'))
                for item in results
            ) if results else 'safe actions'
            yield sse_event('final', {'text': f'Sent open request: {summary}', 'tool': results})
            return

        llm = OllamaClient(
            base_url=os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434'),
            model=select_model(prompt),
        )
        available = await llm.is_available()
        if not available:
            yield sse_event(
                'error',
                {'message': 'Ollama is not available. Start the local model server or install a compatible model.'},
            )
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
