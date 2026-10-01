import asyncio
import json

import httpx

from app.llm import OllamaClient
from app.model_routing import select_model


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
