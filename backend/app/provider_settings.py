"""Session-only provider configuration. Credentials never enter files or responses."""
import base64
import json
from typing import Literal
from urllib.parse import urlparse, quote

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator


PRESETS = {
    'groq': {'label': 'Groq', 'endpoint': 'https://api.groq.com/openai/v1', 'model': 'qwen/qwen3.8-27b',
             'note': 'Free plan available with rate limits. Vision model access depends on your account.',
             'key_url': 'https://console.groq.com/keys'},
    'google': {'label': 'Google Gemini', 'endpoint': 'https://generativelanguage.googleapis.com/v1beta', 'model': 'gemini-3.8-flash',
               'note': 'AI Studio API key. Free-tier eligibility and limits vary; free-tier data may be used to improve Google products.',
               'key_url': 'https://aistudio.google.com/apikey'},
    'openai': {'label': 'OpenAI', 'endpoint': 'https://api.openai.com/v1', 'model': 'gpt-4.1-mini',
               'note': 'Paid API usage; a ChatGPT subscription does not provide API credits.',
               'key_url': 'https://platform.openai.com/api-keys'},
    'anthropic': {'label': 'Anthropic', 'endpoint': 'https://api.anthropic.com/v1', 'model': 'claude-sonnet-4-6',
                  'note': 'Paid API usage; Claude app subscriptions are separate.',
                  'key_url': 'https://platform.claude.com/settings/keys'},
}


class ProviderSettings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    provider: Literal['local', 'cloud'] = 'local'
    service: Literal['custom', 'groq', 'google', 'openai', 'anthropic'] = 'custom'
    model: str = Field(default='qwen3-vl:4b-instruct', min_length=1, max_length=150)
    endpoint: str = Field(default='', max_length=500)
    api_key: SecretStr = Field(default_factory=lambda: SecretStr(''))
    share_screenshots: bool = False

    @model_validator(mode='after')
    def valid_endpoint(self):
        if self.provider == 'cloud':
            if self.service in PRESETS:
                preset = PRESETS[self.service]
                # Pin named-provider credentials to their official API host.
                self.endpoint = preset['endpoint']
                if 'model' not in self.model_fields_set:
                    self.model = preset['model']
            parsed = urlparse(self.endpoint)
            if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError('Cloud endpoint must be an HTTPS API base URL without credentials or query parameters.')
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
        if not self.settings.api_key.get_secret_value().strip():
            raise ValueError('Enter an API key in Settings.')
        if images and not self.settings.share_screenshots:
            raise ValueError('Cloud screen sharing is off. Enable it in Settings to use vision, or select Local.')
        if len(images) > 1 or any(len(image) > 6_000_000 for image in images):
            raise ValueError('Computer image context exceeded its limit.')
        encoded = [base64.b64encode(image).decode('ascii') for image in images]
        instruction = system + '\nReturn only JSON matching this schema: ' + json.dumps(schema)
        service = self.settings.service
        base = self.settings.endpoint.rstrip('/')
        secret = self.settings.api_key.get_secret_value()
        content = [{'type': 'text', 'text': prompt}]
        content.extend({'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(image).decode('ascii')}} for image in images)
        payload = {'model': self.model, 'messages': [
            {'role': 'system', 'content': instruction},
            {'role': 'user', 'content': content if images else prompt}],
            'stream': False, 'response_format': {'type': 'json_object'}}
        url = base + '/chat/completions'
        headers = {'Authorization': 'Bearer ' + secret}
        if service == 'google':
            url = base + '/models/' + quote(self.model.removeprefix('models/'), safe='') + ':generateContent'
            headers = {'x-goog-api-key': secret}
            parts = [{'text': prompt}] + [{'inlineData': {'mimeType': 'image/png', 'data': image}} for image in encoded]
            payload = {'systemInstruction': {'parts': [{'text': instruction}]},
                       'contents': [{'role': 'user', 'parts': parts}],
                       'generationConfig': {'responseMimeType': 'application/json', 'maxOutputTokens': 2048}}
        elif service == 'anthropic':
            url = base + '/messages'
            headers = {'x-api-key': secret, 'anthropic-version': '2023-06-01'}
            content = [{'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png', 'data': image}} for image in encoded]
            content.append({'type': 'text', 'text': prompt})
            payload = {'model': self.model, 'system': system, 'max_tokens': 2048,
                       'messages': [{'role': 'user', 'content': content}],
                       'tools': [{'name': 'agent_decision', 'description': 'Return the next structured agent decision.', 'input_schema': schema}],
                       'tool_choice': {'type': 'tool', 'name': 'agent_decision'}}
        async with httpx.AsyncClient(timeout=60, trust_env=False, follow_redirects=False) as client:
            response = await client.post(url, headers=headers, json=payload)
        if response.is_error:
            # Provider responses may echo prompts/keys; never surface raw response bodies.
            message = {401: 'API key was rejected.', 403: 'The account cannot access this model.',
                       404: 'Model or API endpoint was not found.', 429: 'Rate limit or account quota reached. Wait or check your provider quota.'}.get(
                           response.status_code, 'Check model access and JSON/vision support in Settings.')
            raise RuntimeError(f'Cloud provider returned HTTP {response.status_code}. {message}')
        try:
            data = response.json()
            if service == 'google':
                text = ''.join(part.get('text', '') for part in data['candidates'][0]['content']['parts'] if not part.get('thought'))
            elif service == 'anthropic':
                decision = next(part['input'] for part in data['content'] if part.get('type') == 'tool_use' and part.get('name') == 'agent_decision')
                text = json.dumps(decision)
            else:
                text = data['choices'][0]['message']['content']
            if not isinstance(text, str) or not text.strip():
                raise ValueError('Empty response')
            return text
        except (KeyError, IndexError, TypeError, ValueError, StopIteration) as exc:
            raise RuntimeError('Cloud provider did not return a text completion.') from exc

    async def stream(self, prompt):
        raw = await self.structured(prompt, 'Answer the user in the answer field.',
                                    {'type': 'object', 'properties': {'answer': {'type': 'string'}}, 'required': ['answer']})
        yield json.loads(raw)['answer']
