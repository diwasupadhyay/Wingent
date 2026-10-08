import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app import main
from app.llm import OllamaClient
from app.provider_settings import CloudClient, ProviderSettings


def test_local_model_catalogue_lists_all_installed_names(monkeypatch):
    real_client = httpx.AsyncClient
    def handle(request):
        assert request.url.path == '/api/tags'
        return httpx.Response(200, json={'models': [{'name': 'vision:4b'}, {'name': 'text:3b'}, {'name': 'vision:4b'}]})
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: real_client(transport=httpx.MockTransport(handle), **kw))
    assert TestClient(main.app).get('/api/local-models').json() == {
        'available': True, 'models': ['text:3b', 'vision:4b']}


def test_explicit_model_selection_overrides_legacy_vision_environment(monkeypatch):
    monkeypatch.setenv('OLLAMA_VISION_MODEL', 'old-model')
    assert OllamaClient(model='selected-model').vision_model == 'selected-model'


def test_operator_uses_reference_json_prompting_instead_of_union_grammar(monkeypatch):
    sent = []
    real_client = httpx.AsyncClient
    def handle(request):
        sent.append(json.loads(request.content))
        assert request.url.path == '/api/chat'
        return httpx.Response(200, json={'message': {'content': '{"operations":[{"operation":"done","summary":"Seen"}]}'}})
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: real_client(transport=httpx.MockTransport(handle), **kw))
    asyncio.run(OllamaClient().structured_images('goal', 'system',
        {'type': 'object', 'properties': {'operations': {'type': 'array'}}}, [b'image']))
    assert sent[0]['format'] == 'json'
    assert sent[0]['messages'][-1]['images']


def test_operator_history_preserves_input_error_and_original_goal(monkeypatch):
    sent = []
    real_client = httpx.AsyncClient
    def handle(request):
        sent.append(json.loads(request.content))
        return httpx.Response(200, json={'message': {'content': '{"operations":[]}'}})
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: real_client(transport=httpx.MockTransport(handle), **kw))
    prompt = json.dumps({'objective': 'Type into the selected field', 'recent_actions': [
        {'action': {'operation': 'write', 'content': 'hello'},
         'result': 'error; effect uncertain', 'error': 'Focus changed before typing'}],
        'remaining_work': ['Verify text in destination']})
    asyncio.run(OllamaClient().structured_images(prompt, 'system',
        {'properties': {'operations': {'type': 'array'}}}, [b'image']))
    messages = sent[0]['messages']
    assert messages[1]['content'] == 'Type into the selected field'
    result = messages[3]['content'].removeprefix('Execution result: ')
    assert json.loads(result) == {'result': 'error; effect uncertain', 'error': 'Focus changed before typing'}
    assert json.loads(messages[-1]['content'])['remaining_work'] == ['Verify text in destination']


@pytest.mark.parametrize('status,delay', [(503, 2), (429, 20)])
def test_cloud_transient_retry_is_bounded(monkeypatch, status, delay):
    sent, sleeps = [], []
    real_client = httpx.AsyncClient
    def handle(request):
        sent.append(request)
        return httpx.Response(status, headers={'retry-after': str(delay)})
    async def sleep(seconds):
        sleeps.append(seconds)
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: real_client(transport=httpx.MockTransport(handle), **kw))
    monkeypatch.setattr(asyncio, 'sleep', sleep)
    with pytest.raises(RuntimeError, match=str(status)):
        asyncio.run(CloudClient(ProviderSettings(provider='cloud', service='google', api_key='test')).structured('goal', 'system', {}))
    assert len(sent) == 2 and sleeps == [delay]


def test_context_overflow_retries_with_headroom_and_remembers_size(monkeypatch):
    sent = []
    real_client = httpx.AsyncClient
    def handle(request):
        sent.append(json.loads(request.content))
        if len(sent) == 1:
            return httpx.Response(400, json={'error': {'message': 'request (8222 tokens) exceeds the available context size (8192 tokens)'}})
        return httpx.Response(200, json={'response': '{}'})
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: real_client(transport=httpx.MockTransport(handle), **kw))
    client = OllamaClient()
    for _ in range(2):
        assert asyncio.run(client.structured_images('goal', 'system', {}, [b'image'])) == '{}'
    assert [r['options']['num_ctx'] for r in sent] == [8192, 16384, 16384]
    assert sent[0]['images'] == sent[1]['images']


def test_connection_and_synthetic_vision_do_not_save_or_capture(monkeypatch):
    import struct
    import zlib
    monkeypatch.setattr(main, 'provider_settings', None)
    async def structured(self, *args):
        return '{"ok":true}'
    async def vision(self, prompt, system, schema, images):
        image = images[0]
        size = struct.unpack('>I', image[33:37])[0]
        rgb = tuple(zlib.decompress(image[41:41 + size])[1:4])
        return json.dumps({'color': {(255, 0, 0): 'red', (0, 128, 0): 'green', (0, 0, 255): 'blue'}[rgb]})
    monkeypatch.setattr(CloudClient, 'structured', structured)
    monkeypatch.setattr(CloudClient, 'structured_images', vision)
    client = TestClient(main.app)
    config = {'provider': 'cloud', 'service': 'groq', 'api_key': 'test-only'}
    for endpoint in ['/api/settings/test', '/api/settings/test?vision=true']:
        assert client.post(endpoint, json=config).json()['ready'] is True
        assert main.provider_settings is None
        assert client.post(endpoint, json=config, headers={'Origin': 'https://evil.example'}).status_code == 403


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
