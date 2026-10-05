import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app import main
from app.llm import OllamaClient
from app.provider_settings import CloudClient, ProviderSettings


@pytest.mark.parametrize('service', ['groq', 'openai', 'google', 'anthropic'])
def test_provider_presets_use_official_auth_and_vision_wire_format(monkeypatch, service):
    sent = []
    real_client = httpx.AsyncClient
    def handle(request):
        sent.append(request)
        if service == 'google':
            body = {'candidates': [{'content': {'parts': [{'text': '{"tool":"finish"}'}]}}]}
        elif service == 'anthropic':
            body = {'content': [{'type': 'tool_use', 'name': 'agent_decision', 'input': {'tool': 'finish'}}]}
        else:
            body = {'choices': [{'message': {'content': '{"tool":"finish"}'}}]}
        return httpx.Response(200, json=body)
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs))
    settings = ProviderSettings(provider='cloud', service=service, endpoint='https://untrusted.example', api_key='secret-test', share_screenshots=True)
    result = asyncio.run(CloudClient(settings).structured_images('goal', 'system', {'type': 'object'}, [b'image']))
    request = sent[0]
    assert request.url.host != 'untrusted.example'
    assert settings.model != 'qwen3-vl:4b-instruct'
    assert json.loads(result)['tool'] == 'finish'
    body = json.loads(request.content)
    assert 'secret-test' not in str(request.url) and 'secret-test' not in request.content.decode()
    if service == 'google':
        assert request.headers['x-goog-api-key'] == 'secret-test'
        assert body['contents'][0]['parts'][1]['inlineData']['mimeType'] == 'image/png'
        assert request.url.path.endswith(':generateContent')
    elif service == 'anthropic':
        assert request.headers['x-api-key'] == 'secret-test'
        assert body['messages'][0]['content'][0]['source']['type'] == 'base64'
        assert body['tool_choice']['name'] == 'agent_decision'
    else:
        assert request.headers['authorization'] == 'Bearer secret-test'
        assert body['messages'][1]['content'][1]['type'] == 'image_url'


def test_saved_key_cannot_follow_a_provider_change(monkeypatch):
    monkeypatch.setattr(main, 'provider_settings', None)
    client = TestClient(main.app)
    assert client.post('/api/settings', json={'provider': 'cloud', 'service': 'groq', 'api_key': 'secret-test'}).status_code == 200
    assert client.post('/api/settings', json={'provider': 'cloud', 'service': 'groq', 'model': 'another-model'}).status_code == 200
    assert client.post('/api/settings', json={'provider': 'cloud', 'service': 'google'}).status_code == 422
    assert main.provider_settings.service == 'groq'


def test_settings_never_return_keys_and_reject_foreign_origin(monkeypatch):
    monkeypatch.setattr(main, 'provider_settings', None)
    client = TestClient(main.app)
    data = dict(provider='cloud', model='vision-model', endpoint='https://provider.example/v1', api_key='private-test-key')
    response = client.post('/api/settings', json=data, headers={'Origin': 'https://untrusted.example'})
    assert response.status_code == 403
    response = client.post('/api/settings', json=data, headers={'Origin': 'http://tauri.localhost'})
    assert response.status_code == 200
    assert 'private-test-key' not in response.text
    assert 'private-test-key' not in client.get('/api/settings').text
    data['endpoint'] = 'http://provider.example'
    response = client.post('/api/settings', json=data)
    assert response.status_code == 422
    assert 'private-test-key' not in response.text


def test_cloud_vision_requires_consent_and_uses_selected_endpoint(monkeypatch):
    sent = []
    real_client = httpx.AsyncClient
    def handle(request):
        sent.append(request)
        return httpx.Response(200, json={'choices': [{'message': {'content': '{"tool":"finish"}'}}]})
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs))
    settings = ProviderSettings(provider='cloud', model='vision-model', endpoint='https://provider.example/v1', api_key='test-key')
    with pytest.raises(ValueError, match='sharing is off'):
        asyncio.run(CloudClient(settings).structured_images('goal', 'system', {}, [b'image']))
    assert not sent
    settings.share_screenshots = True
    result = asyncio.run(CloudClient(settings).structured_images('goal', 'system', {}, [b'image']))
    assert json.loads(result)['tool'] == 'finish'
    assert str(sent[0].url) == 'https://provider.example/v1/chat/completions'
    assert sent[0].headers['authorization'] == 'Bearer test-key'
    body = json.loads(sent[0].content)
    assert body['model'] == 'vision-model'
    assert body['messages'][1]['content'][1]['image_url']['url'].startswith('data:image/png;base64,')


@pytest.mark.parametrize('reason,retries', [('invalid JSON schema grammar', 1), ('model does not support images', 0)])
def test_ollama_retries_only_schema_rejection(monkeypatch, reason, retries):
    requests = []
    real_client = httpx.AsyncClient
    def handle(request):
        requests.append(json.loads(request.content))
        return httpx.Response(400, json={'error': reason}) if len(requests) == 1 else httpx.Response(200, json={'response': '{}'})
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs))
    if retries:
        assert asyncio.run(OllamaClient().structured('goal', 'system', {})) == '{}'
        assert requests[1]['format'] == 'json'
    else:
        with pytest.raises(RuntimeError, match='support images'):
            asyncio.run(OllamaClient().structured('goal', 'system', {}))
    assert len(requests) == 1 + retries
