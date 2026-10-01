from fastapi.testclient import TestClient

from app.main import app, detect_deterministic_tools, requests_unsupported_browser_automation
from app.tools import ToolPermission, ToolRegistry

client = TestClient(app)


def test_health_endpoint():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_command_validation_rejects_blank_prompt():
    response = client.post('/api/command', json={'prompt': ''})
    assert response.status_code == 422


def test_tauri_origin_can_preflight_command_endpoint():
    response = client.options(
        '/api/command',
        headers={
            'Origin': 'http://tauri.localhost',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'content-type',
        },
    )

    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == 'http://tauri.localhost'


def test_registry_has_safe_open_tools():
    registry = ToolRegistry()
    open_url = registry.get_tool('open_url')
    open_app = registry.get_tool('open_application')

    assert open_url is not None
    assert open_app is not None
    assert open_url.permission.value == 'safe'
    assert open_app.permission.value == 'safe'


def test_registry_executes_safe_actions(monkeypatch):
    monkeypatch.setattr('app.tools.webbrowser.open', lambda *_args, **_kwargs: True)
    registry = ToolRegistry()
    result = registry.execute('open_url', {'url': 'https://example.com'})

    assert result['ok'] is True
    assert result['action'] == 'open_url'
    assert result['url'] == 'https://example.com'


def test_registry_rejects_invalid_urls():
    registry = ToolRegistry()

    try:
        registry.execute('open_url', {'url': 'file:///c:/secret.txt'})
    except ValueError as exc:
        assert str(exc) == 'Only HTTP and HTTPS URLs are allowed.'
    else:
        raise AssertionError('Expected non-web URL to be rejected')


def test_browser_launch_failure_is_reported(monkeypatch):
    monkeypatch.setattr('app.tools.webbrowser.open', lambda *_args, **_kwargs: False)
    registry = ToolRegistry()
    try:
        registry.execute('open_url', {'url': 'https://example.com'})
    except RuntimeError as exc:
        assert 'did not accept' in str(exc)
    else:
        raise AssertionError('Expected browser launch failure')


def test_registry_requires_confirmation_for_consequential_tools():
    registry = ToolRegistry()
    registry.register(
        'delete_file',
        'Delete a file.',
        permission=ToolPermission.CONFIRMATION_REQUIRED,
        input_schema={'type': 'object'},
        executor=lambda _: {'ok': True},
    )

    try:
        registry.execute('delete_file')
    except PermissionError as exc:
        assert 'Confirmation is required' in str(exc)
    else:
        raise AssertionError('Expected confirmation gate to reject execution')


def test_detect_deterministic_tools_handles_multiple_safe_actions():
    actions = detect_deterministic_tools('Open Chrome and open https://example.com')

    assert actions == [('open_url', {'url': 'https://example.com'})]


def test_detect_deterministic_tools_normalizes_bare_domains():
    actions = detect_deterministic_tools('open example.com')

    assert actions == [('open_url', {'url': 'https://example.com'})]


def test_detect_deterministic_tools_opens_youtube_directly():
    actions = detect_deterministic_tools('open youtube')

    assert actions == [('open_url', {'url': 'https://www.youtube.com'})]


def test_detect_deterministic_tools_searches_youtube_without_duplicate_launch():
    actions = detect_deterministic_tools('Open Chrome and open youtube and search piano tutorials')

    assert actions == [
        (
            'open_url',
            {'url': 'https://www.youtube.com/results?search_query=piano+tutorials'},
        )
    ]


def test_profile_selection_is_reported_as_unsupported_browser_automation():
    assert requests_unsupported_browser_automation('Open Chrome and select any profile') is True


def test_mixed_browser_task_is_not_partially_executed(monkeypatch):
    executed = []
    monkeypatch.setattr('app.main.registry.execute', lambda *args, **kwargs: executed.append((args, kwargs)))

    response = client.post(
        '/api/command',
        json={'prompt': 'Open Chrome, go to Gmail, and check whether I have important emails'},
    )

    assert response.status_code == 200
    assert 'event: error' in response.text
    assert 'unsupported_action' in response.text
    assert executed == []


def test_supported_actions_run_without_model(monkeypatch):
    executed = []

    def record_execution(name, params):
        executed.append((name, params))
        return {'ok': True, 'action': name}

    monkeypatch.setattr('app.main.registry.execute', record_execution)
    response = client.post('/api/command', json={'prompt': 'Open Chrome and open https://example.com'})

    assert 'event: final' in response.text
    assert executed == [('open_url', {'url': 'https://example.com'})]


def test_unknown_step_cancels_entire_deterministic_plan():
    assert detect_deterministic_tools('Open Chrome and check Gmail') == []
    assert detect_deterministic_tools('Open YouTube and send an email') == []


def test_safe_search_routes_without_model():
    assert detect_deterministic_tools('search Google for local AI agents') == [
        ('open_url', {'url': 'https://www.google.com/search?q=local+AI+agents'})
    ]


def test_polite_safe_command_is_supported():
    assert detect_deterministic_tools('Could you open Notepad?') == [
        ('open_application', {'application': 'notepad'})
    ]


def test_empty_model_stream_is_error(monkeypatch):
    async def available(_self):
        return True

    async def empty_stream(_self, _prompt):
        if False:
            yield ''

    monkeypatch.setattr('app.main.OllamaClient.is_available', available)
    monkeypatch.setattr('app.main.OllamaClient.stream', empty_stream)

    response = client.post('/api/command', json={'prompt': 'What is Wingent?'})
    assert 'event: error' in response.text
    assert 'returned no response' in response.text
    assert 'event: final' not in response.text
