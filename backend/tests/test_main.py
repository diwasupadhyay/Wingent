import json

from fastapi.testclient import TestClient
from app import main


def test_health_and_new_engine():
    client = TestClient(main.app)
    assert client.get('/health').json()['runtime'] == 'wingent-desktop-v3'
    assert client.get('/api/capabilities').json()['engine'] == 'self-operating-computer'
    assert client.post('/api/command', json={'prompt': '  '}).status_code == 422


def test_tauri_origin():
    response = TestClient(main.app).options('/api/command', headers={
        'Origin': 'http://tauri.localhost', 'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'content-type'})
    assert response.status_code == 200


def test_command_uses_screenshot_engine(monkeypatch):
    seen = []
    class Provider:
        async def is_available(self): return True
    async def run(goal, provider, disconnected, approvals, review_actions=False):
        seen.append((goal, review_actions))
        yield 'final', {'outcome': 'completed', 'verified': False, 'text': 'Visual completion'}
    monkeypatch.setattr(main, 'make_provider', lambda _: Provider())
    monkeypatch.setattr(main, 'run_self_operating', run)
    result = TestClient(main.app).post('/api/command', json={'prompt': 'Open Calculator'})
    assert result.status_code == 200
    assert seen == [('Open Calculator', False)]
    assert 'event: final' in result.text


def test_missing_model_returns_error(monkeypatch):
    class Provider:
        last_availability = {'code': 'missing', 'message': 'Model missing'}
        async def is_available(self): return False
    monkeypatch.setattr(main, 'make_provider', lambda _: Provider())
    response = TestClient(main.app).post('/api/command', json={'prompt': 'Open app'})
    assert 'Model missing' in response.text


def test_approval_endpoint_keeps_exact_token_binding():
    approval = main.approvals.request('test', 'click', 'soc-1', {'x': 0.2})
    client = TestClient(main.app)
    assert client.post('/api/approvals/' + approval.id,
        json={'token': 'wrong', 'approve': True}).status_code == 409
    assert client.post('/api/approvals/' + approval.id,
        json={'token': approval.token, 'approve': False}).status_code == 200
    main.approvals.revoke_task('test')
