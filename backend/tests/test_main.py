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


def test_registry_executes_safe_actions():
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
