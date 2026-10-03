import json
import os
import asyncio
from typing import AsyncIterator, Protocol

import httpx


class LLMProvider(Protocol):
    async def is_available(self) -> bool: ...

    def stream(self, prompt: str) -> AsyncIterator[str]: ...

    async def structured(self, prompt: str, system: str, schema: dict) -> str: ...


_SYSTEM_INSTRUCTION = (
    'You are Wingent, a local text assistant. Answer clearly and briefly. '
    'You cannot inspect the user\'s screen, browser, email, files, or applications. '
    'You cannot execute actions through this model response. '
    'Never claim to have performed an action or observed private data that was not supplied in the prompt.'
)


class OllamaClient:
    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        self.base_url = (base_url or os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')).rstrip('/')
        self.model = model or os.getenv('OLLAMA_MODEL', 'qwen3-vl:4b-instruct')
        self.last_availability = None

    async def is_available(self) -> bool:
        return (await self.availability(retry=True))['ready']

    async def availability(self, retry=False) -> dict:
        """Check the API/model, not just its port; retry only transient readiness failures."""
        for attempt in range(2 if retry else 1):
            try:
                async with httpx.AsyncClient(timeout=5.0, trust_env=False) as client:
                    response = await client.get(f'{self.base_url}/api/tags')
                if response.status_code != 200:
                    code, message = 'ollama_http_error', f'Ollama returned HTTP {response.status_code}. Check the configured Ollama server.'
                else:
                    payload = response.json()
                    if not isinstance(payload, dict) or not isinstance(payload.get('models'), list):
                        raise ValueError('Invalid model catalogue')
                    names = [item.get('name') or item.get('model') for item in payload['models'] if isinstance(item, dict)]
                    # Ollama expands an omitted tag to :latest in its catalogue.
                    selected = self.model if ':' in self.model.rsplit('/', 1)[-1] else self.model + ':latest'
                    installed = any(name == self.model or name == selected for name in names)
                    if installed:
                        code, message = 'ready', f'Ollama is ready with {self.model}.'
                    else:
                        code, message = 'ollama_model_missing', (
                            f'Ollama is running, but model "{self.model}" is not installed. '
                            f'Install that model or set OLLAMA_MODEL to an installed model, then restart Wingent. '
                            'Installed models: ' + ', '.join(str(name) for name in names[:12] if name))
            except httpx.TimeoutException:
                code, message = 'ollama_timeout', 'Ollama is not responding yet. It may still be starting or busy. Wait a moment, then retry.'
            except httpx.RequestError:
                code, message = 'ollama_unreachable', 'Cannot connect to Ollama. Use Start Ollama, or check OLLAMA_BASE_URL if you configured another server.'
            except (ValueError, TypeError):
                code, message = 'ollama_invalid_response', 'The configured server did not return a valid Ollama model list.'
            self.last_availability = {'ready': code == 'ready', 'code': code, 'message': message, 'model': self.model}
            if code not in {'ollama_timeout', 'ollama_unreachable'} or not retry or attempt:
                break
            await asyncio.sleep(0.3)
        return self.last_availability

    async def structured(self, prompt: str, system: str, schema: dict) -> str:
        async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
            response = await client.post(f'{self.base_url}/api/generate', json={
                'model': self.model, 'system': system, 'prompt': prompt,
                'stream': False, 'format': schema,
                'options': {'temperature': 0, 'num_predict': 1200, 'num_ctx': 8192},
            })
            response.raise_for_status()
            payload = response.json()
            if payload.get('error'):
                raise RuntimeError(f'Ollama error: {payload["error"]}')
            return payload.get('response', '')

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
            async with client.stream(
                'POST',
                f'{self.base_url}/api/generate',
                json={
                    'model': self.model,
                    'system': _SYSTEM_INSTRUCTION,
                    'prompt': prompt,
                    'stream': True,
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if payload.get('error'):
                        raise RuntimeError(f'Ollama error: {payload["error"]}')
                    text = payload.get('response', '')
                    if text:
                        yield text
