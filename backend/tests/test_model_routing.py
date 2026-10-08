import asyncio
import json

import httpx

from app.llm import OllamaClient
from app.model_routing import select_model


def test_explicit_thinking_control_is_forwarded(monkeypatch):
    monkeypatch.setenv('OLLAMA_THINK', 'false')
    def handle(request):
        assert json.loads(request.content)['think'] is False
        return httpx.Response(200, json={'response': '{}'})
    real_client = httpx.AsyncClient
    monkeypatch.setattr('app.llm.httpx.AsyncClient', lambda **kwargs: real_client(
        transport=httpx.MockTransport(handle), **kwargs))
    assert asyncio.run(OllamaClient().structured('test', 'test', {})) == '{}'


def test_thinking_only_response_is_explicit_without_exposing_trace(monkeypatch):
    import pytest
    real_client = httpx.AsyncClient
    monkeypatch.setattr('app.llm.httpx.AsyncClient', lambda **kwargs: real_client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200,
            json={'response': '', 'thinking': 'private trace'})), **kwargs))
    with pytest.raises(RuntimeError, match='thinking without an action') as error:
        asyncio.run(OllamaClient().structured('test', 'test', {}))
    assert 'private trace' not in str(error.value)


def test_new_local_default_is_configurable(monkeypatch):
    monkeypatch.delenv('OLLAMA_MODEL', raising=False)
    monkeypatch.delenv('OLLAMA_COMPLEX_MODEL', raising=False)
    assert select_model('Find an installed app') == 'qwen3-vl:4b-instruct'


def test_model_availability_requires_selected_model(monkeypatch):
    import asyncio
    import httpx
    class Client:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def get(self, url):
            return httpx.Response(200, json={'models': [{'name': 'llama3.2:3b'}]})
    monkeypatch.setattr('app.llm.httpx.AsyncClient', lambda **kwargs: Client())
    assert asyncio.run(OllamaClient(model='qwen3-vl:4b-instruct').is_available()) is False


def test_transient_startup_timeout_is_retried_without_model_download(monkeypatch):
    calls = []
    def handle(request):
        calls.append(request.url.path)
        if len(calls) == 1:
            raise httpx.ReadTimeout('starting')
        return httpx.Response(200, json={'models': [{'name': 'qwen3-vl:4b-instruct'}]})
    real_client = httpx.AsyncClient
    def client(**kwargs):
        assert kwargs['trust_env'] is False
        return real_client(transport=httpx.MockTransport(handle), **kwargs)
    monkeypatch.setattr('app.llm.httpx.AsyncClient', client)
    model = OllamaClient(model='qwen3-vl:4b-instruct')
    assert asyncio.run(model.is_available()) is True
    assert calls == ['/api/tags', '/api/tags']


def test_missing_model_reports_selected_and_installed_names_without_retry(monkeypatch):
    calls = []
    def handle(request):
        calls.append(request.url.path)
        return httpx.Response(200, json={'models': [{'name': 'available:latest'}]})
    real_client = httpx.AsyncClient
    monkeypatch.setattr('app.llm.httpx.AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs))
    model = OllamaClient(model='missing:4b')
    assert asyncio.run(model.is_available()) is False
    assert model.last_availability['code'] == 'ollama_model_missing'
    assert 'missing:4b' in model.last_availability['message'] and 'available:latest' in model.last_availability['message']
    assert len(calls) == 1


def test_untagged_model_matches_latest_and_malformed_server_is_explicit(monkeypatch):
    replies = [{'models': [{'name': 'local:latest'}]}, {'models': None}]
    real_client = httpx.AsyncClient
    monkeypatch.setattr('app.llm.httpx.AsyncClient', lambda **kwargs: real_client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=replies.pop(0))), **kwargs))
    model = OllamaClient(model='local')
    assert asyncio.run(model.is_available()) is True
    assert asyncio.run(model.availability())['code'] == 'ollama_invalid_response'


def test_fast_model_remains_default(monkeypatch):
    monkeypatch.setenv('OLLAMA_MODEL', 'small:latest')
    monkeypatch.setenv('OLLAMA_COMPLEX_MODEL', 'large:latest')
    assert select_model('What is 2 + 2?') == 'small:latest'


def test_complex_model_is_opt_in(monkeypatch):
    monkeypatch.setenv('OLLAMA_MODEL', 'small:latest')
    monkeypatch.delenv('OLLAMA_COMPLEX_MODEL', raising=False)
    assert select_model('Compare these two approaches') == 'small:latest'
    monkeypatch.setenv('OLLAMA_COMPLEX_MODEL', 'large:latest')
    assert select_model('Compare these two approaches') == 'large:latest'


def test_model_receives_capability_boundary(monkeypatch):
    requests = []

    def handle(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, text='{"response":"Hello","done":false}\n')

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        'app.llm.httpx.AsyncClient',
        lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs),
    )

    async def collect():
        return [part async for part in OllamaClient(model='small:latest').stream('Hello')]

    assert asyncio.run(collect()) == ['Hello']
    assert requests[0]['model'] == 'small:latest'
    assert 'cannot inspect' in requests[0]['system']


def test_model_error_is_not_silently_discarded(monkeypatch):
    def handle(_request):
        return httpx.Response(200, text='{"error":"model not found"}\n')

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        'app.llm.httpx.AsyncClient',
        lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs),
    )

    async def collect():
        return [part async for part in OllamaClient().stream('Hello')]

    try:
        asyncio.run(collect())
    except RuntimeError as error:
        assert 'model not found' in str(error)
    else:
        raise AssertionError('Expected Ollama error to be surfaced')
