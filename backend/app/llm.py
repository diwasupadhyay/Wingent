import json
import os
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
        self.model = model or os.getenv('OLLAMA_MODEL', 'llama3.2:3b')

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f'{self.base_url}/api/tags')
                return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def structured(self, prompt: str, system: str, schema: dict) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
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
        async with httpx.AsyncClient(timeout=60.0) as client:
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
