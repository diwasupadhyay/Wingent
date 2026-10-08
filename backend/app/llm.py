import json
import os
import asyncio
import base64
import re
from urllib.parse import urlparse
from typing import AsyncIterator, Protocol

import httpx


class LLMProvider(Protocol):
    async def is_available(self) -> bool: ...

    def stream(self, prompt: str) -> AsyncIterator[str]: ...

    async def structured(self, prompt: str, system: str, schema: dict) -> str: ...

    async def structured_images(self, prompt: str, system: str, schema: dict, images: list[bytes]) -> str: ...


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
        self.vision_model = model or os.getenv('OLLAMA_VISION_MODEL') or self.model
        self.last_availability = None
        self.context_size = 8192

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
        return await self._generate(prompt, system, schema)

    async def structured_images(self, prompt, system, schema, images):
        parsed = urlparse(self.base_url)
        if parsed.scheme != 'http' or parsed.hostname not in {'127.0.0.1', 'localhost', '::1'} or parsed.username or parsed.password:
            raise ValueError('Computer screenshots require a local Ollama endpoint.')
        if len(images) > 1 or any(len(image) > 6_000_000 for image in images):
            raise ValueError('Computer image context exceeded its limit.')
        return await self._generate(prompt, system, schema, images)

    async def _generate(self, prompt, system, schema, images=None):
        payload = {
            'model': self.vision_model if images else self.model,
            'system': system, 'prompt': prompt, 'stream': False, 'format': schema,
            'options': {'temperature': 0, 'num_predict': 1200, 'num_ctx': self.context_size},
            'keep_alive': '10m',
        }
        thinking = os.getenv('OLLAMA_THINK', 'auto').strip().lower()
        if thinking != 'auto':
            if thinking not in {'true', 'false', 'low', 'medium', 'high'}:
                raise ValueError('OLLAMA_THINK must be auto, true, false, low, medium, or high.')
            payload['think'] = thinking == 'true' if thinking in {'true', 'false'} else thinking
        if 'operations' in schema.get('properties', {}):
            # The upstream operator prompts for JSON and validates afterwards.
            # Avoid a union grammar steering small vision models into an action
            # name before they have described the intended operation.
            payload['format'] = 'json'
        if images:
            payload['images'] = [base64.b64encode(image).decode('ascii') for image in images]
        endpoint = '/api/generate'
        if images and 'operations' in schema.get('properties', {}):
            # Match upstream's Ollama chat loop: distinguish executed assistant
            # actions from the latest user observation instead of one flat prompt.
            endpoint = '/api/chat'
            messages = [{'role': 'system', 'content': payload.pop('system')}]
            try:
                context = json.loads(prompt)
                history = context.pop('recent_actions', [])
                messages.append({'role': 'user', 'content': context.get('objective', '')})
                for record in history[-8:]:
                    if record.get('action'):
                        messages.append({'role': 'assistant', 'content': json.dumps({'operations': [record['action']]})})
                        # Preserve why native input failed; otherwise the model
                        # sees only "uncertain" and cannot choose a useful repair.
                        result = {key: value for key, value in record.items() if key != 'action'}
                        messages.append({'role': 'user', 'content': 'Execution result: ' +
                                         json.dumps(result, separators=(',', ':'))})
                    else:
                        messages.append({'role': 'user', 'content': json.dumps(record)})
                latest = json.dumps(context)
            except (ValueError, AttributeError, TypeError):
                latest = prompt
            messages.append({'role': 'user', 'content': latest, 'images': payload.pop('images')})
            payload.pop('prompt')
            payload['messages'] = messages
        async with httpx.AsyncClient(timeout=110.0, trust_env=False) as client:
            response = await client.post(self.base_url + endpoint, json=payload)
            if response.status_code == 400:
                try:
                    reason = str(response.json().get('error', '')).lower()
                except (ValueError, AttributeError):
                    reason = ''
                if 'exceed' in reason and 'context' in reason:
                    match = re.search(r'request \((\d+) tokens\)', reason)
                    required = int(match.group(1)) + 1200 if match else 16384
                    context_size = max(16384, 1 << (required - 1).bit_length())
                    if context_size <= 32768:
                        # The rejected inference executed no tools. Retry once
                        # with output headroom; never silently truncate the goal.
                        payload['options']['num_ctx'] = context_size
                        response = await client.post(self.base_url + endpoint, json=payload)
                        if not response.is_error:
                            self.context_size = context_size
                elif any(word in reason for word in ('schema', 'grammar', 'format')):
                    # Some installed runners reject recursive JSON schemas.
                    # Retry only that rejected inference, never a computer action.
                    payload['format'] = 'json'
                    if 'messages' in payload:
                        payload['messages'][0]['content'] += '\nReturn JSON matching this schema: ' + json.dumps(schema)
                    else:
                        payload['system'] += '\nReturn JSON matching this schema: ' + json.dumps(schema)
                    response = await client.post(self.base_url + endpoint, json=payload)
            if response.is_error:
                try:
                    detail = str(response.json().get('error', 'No error detail returned'))[:500]
                except (ValueError, AttributeError):
                    detail = 'Invalid error response'
                raise RuntimeError(f'Ollama rejected the {"vision" if images else "text"} request '
                                   f'for {payload["model"]} (HTTP {response.status_code}): {detail}')
            response.raise_for_status()
            payload = response.json()
            if payload.get('error'):
                raise RuntimeError(f'Ollama error: {payload["error"]}')
            answer = payload.get('message', {}).get('content', '') if endpoint == '/api/chat' else payload.get('response', '')
            reasoning_present = bool(payload.get('thinking') or payload.get('message', {}).get('thinking'))
            if not answer.strip() and reasoning_present:
                raise RuntimeError('Ollama returned thinking without an action response. '
                                   'For models that support it, set OLLAMA_THINK=false, or choose an instruct vision model.')
            return answer

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
