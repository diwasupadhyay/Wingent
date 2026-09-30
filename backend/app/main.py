import asyncio
import json
import os
import re
from typing import AsyncGenerator
from urllib.parse import quote_plus

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.llm import OllamaClient
from app.models import CommandRequest
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


def detect_deterministic_tools(prompt: str) -> list[tuple[str, dict[str, str]]]:
    segments = re.split(r'\b(?:and|then|also)\b', prompt, flags=re.IGNORECASE)
    actions: list[tuple[str, dict[str, str]]] = []
    youtube_search = re.search(
        r'\b(?:search|look up|find)\s+(?:for\s+)?(.+?)(?:\s+on\s+youtube)?(?:[.!?]|$)',
        prompt,
        flags=re.IGNORECASE,
    )
    has_youtube = bool(re.search(r'\byoutube\b', prompt, flags=re.IGNORECASE))

    if has_youtube and youtube_search:
        query = youtube_search.group(1).strip(' .,!?:;')
        if query:
            return [
                (
                    'open_url',
                    {'url': f'https://www.youtube.com/results?search_query={quote_plus(query)}'},
                )
            ]

    for segment in segments:
        cleaned = segment.strip()
        if not cleaned:
            continue

        lowered = cleaned.lower()
        for app_name in ('chrome', 'google chrome', 'edge', 'msedge', 'notepad', 'explorer'):
            if re.search(rf'\b(?:open|launch|start)\s+{re.escape(app_name)}\b', lowered):
                actions.append(('open_application', {'application': app_name}))
                break

        url_match = re.search(
            r'(?:(?:https?://)|(?:www\.))[^\s,]+|\b[a-z0-9][a-z0-9.-]+\.(?:com|org|net|io|dev)\b',
            cleaned,
            flags=re.IGNORECASE,
        )
        if url_match:
            url = url_match.group(0).rstrip('.,!?;:')
            if not re.match(r'^https?://', url, flags=re.IGNORECASE):
                url = f'https://{url}'
            actions.append(('open_url', {'url': url}))
        elif re.search(r'\byoutube\b', lowered):
            actions.append(('open_url', {'url': 'https://www.youtube.com'}))

    if any(tool_name == 'open_url' for tool_name, _ in actions):
        actions = [
            (tool_name, params)
            for tool_name, params in actions
            if tool_name != 'open_application'
        ]

    return actions


def requests_unsupported_browser_automation(prompt: str) -> bool:
    return bool(
        re.search(
            r'\b(?:select|choose|pick)\b.{0,32}\b(?:profile|account)\b',
            prompt,
            flags=re.IGNORECASE,
        )
    )


@app.post('/api/command')
async def command(request: Request, command_request: CommandRequest) -> StreamingResponse:
    prompt = command_request.prompt.strip()
    llm = OllamaClient(
        base_url=os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434'),
        model=os.getenv('OLLAMA_MODEL', 'llama3.2:3b'),
    )

    async def event_stream() -> AsyncGenerator[str, None]:
        yield sse_event('status', {'stage': 'planning', 'message': 'Planning request'})
        await asyncio.sleep(0.15)

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
        if deterministic_actions:
            results: list[dict[str, object]] = []
            for index, (tool_name, params) in enumerate(deterministic_actions, start=1):
                tool = registry.get_tool(tool_name)
                if tool is None:
                    yield sse_event('error', {'message': 'No matching tool is available.'})
                    return

                yield sse_event(
                    'status',
                    {
                        'stage': 'tool_running',
                        'message': f'Running {tool_name} ({index}/{len(deterministic_actions)})',
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
                f"{item.get('action', 'tool')}" for item in results
            ) if results else 'safe actions'
            yield sse_event('final', {'text': f'Completed safe actions: {summary}', 'tool': results})
            return

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

        result = ''.join(full).strip() or 'I am ready to help with the task.'
        yield sse_event('final', {'text': result})

    return StreamingResponse(event_stream(), media_type='text/event-stream')
