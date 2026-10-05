"""Session-only provider configuration. Credentials never enter files or responses."""
import base64
import json
from typing import Literal
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator


class ProviderSettings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    provider: Literal['local', 'cloud'] = 'local'
    model: str = Field(default='qwen3-vl:4b-instruct', min_length=1, max_length=150)
    endpoint: str = Field(default='', max_length=500)
    api_key: SecretStr = Field(default_factory=lambda: SecretStr(''))
    share_screenshots: bool = False

    @model_validator(mode='after')
    def valid_endpoint(self):
        if self.provider == 'cloud':
            parsed = urlparse(self.endpoint)
            if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError('Cloud endpoint must be an HTTPS API base URL without credentials or query parameters.')
            if not self.api_key.get_secret_value().strip():
                raise ValueError('Enter an API key for the cloud provider.')
        return self

    def public(self):
        return {**self.model_dump(exclude={'api_key'}), 'key_configured': bool(self.api_key.get_secret_value())}


class CloudClient:
    """Chat Completions compatible text/vision provider; no automatic cloud fallback."""
    def __init__(self, settings):
        self.settings = settings.model_copy(deep=True)
        self.model = settings.model
        self.last_availability = None

    async def availability(self, retry=False):
        # Saving settings does not spend tokens or transmit screen contents.
        self.last_availability = {'ready': True, 'code': 'configured', 'model': self.model,
                                  'message': f'Cloud configured: {self.model}. Connection checked on first task.'}
        return self.last_availability

    async def is_available(self):
        return (await self.availability())['ready']

    async def structured(self, prompt, system, schema):
        return await self.structured_images(prompt, system, schema, [])

    async def structured_images(self, prompt, system, schema, images):
        if images and not self.settings.share_screenshots:
            raise ValueError('Cloud screen sharing is off. Enable it in Settings to use vision, or select Local.')
        if len(images) > 1 or any(len(image) > 6_000_000 for image in images):
            raise ValueError('Computer image context exceeded its limit.')
        content = [{'type': 'text', 'text': prompt}]
        content.extend({'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(image).decode('ascii')}} for image in images)
        payload = {'model': self.model, 'messages': [
            {'role': 'system', 'content': system + '\nReturn only JSON matching this schema: ' + json.dumps(schema)},
            {'role': 'user', 'content': content if images else prompt}],
            'stream': False, 'response_format': {'type': 'json_object'}}
        async with httpx.AsyncClient(timeout=60, trust_env=False, follow_redirects=False) as client:
            response = await client.post(self.settings.endpoint.rstrip('/') + '/chat/completions',
                                         headers={'Authorization': 'Bearer ' + self.settings.api_key.get_secret_value()}, json=payload)
        if response.is_error:
            # Provider responses may echo prompts/keys; never surface raw response bodies.
            raise RuntimeError(f'Cloud provider returned HTTP {response.status_code}. Check endpoint, key, model and JSON/vision support in Settings.')
        try:
            text = response.json()['choices'][0]['message']['content']
            if not isinstance(text, str) or not text.strip():
                raise ValueError('Empty response')
            return text
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise RuntimeError('Cloud provider did not return a text completion.') from exc

    async def stream(self, prompt):
        raw = await self.structured(prompt, 'Answer the user in the answer field.',
                                    {'type': 'object', 'properties': {'answer': {'type': 'string'}}, 'required': ['answer']})
        yield json.loads(raw)['answer']
