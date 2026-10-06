import json

from fastapi.testclient import TestClient

from app.main import app
from app.routing import detect_deterministic_tools, requests_unsupported_browser_automation
from app.tools import ToolPermission, ToolRegistry

client = TestClient(app)


def test_production_has_one_computer_control_protocol():
    from app.main import registry
    names = {tool['name'] for tool in registry.manifest()}
    assert {'computer_begin', 'computer_observe', 'computer_action'} <= names
    assert not any(name.startswith('desktop_') or name == 'screen_inspect' for name in names)


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

    assert actions == [('open_url', {'url': 'https://example.com', 'browser': 'chrome'})]


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
            {'url': 'https://www.youtube.com/results?search_query=piano+tutorials', 'browser': 'chrome'},
        )
    ]


def test_profile_selection_is_reported_as_unsupported_browser_automation():
    assert requests_unsupported_browser_automation('Open Chrome and select any profile') is True


def test_mixed_browser_task_is_not_partially_executed(monkeypatch):
    async def clarify(*args):
        return '{"tool":"ask","message":"Reading email is not available. No actions were taken."}'
    async def available(*args):
        return True
    monkeypatch.setattr('app.main.OllamaClient.structured', clarify)
    monkeypatch.setattr('app.main.OllamaClient.is_available', available)
    executed = []
    monkeypatch.setattr('app.main.registry.execute', lambda *args, **kwargs: executed.append((args, kwargs)))

    response = client.post(
        '/api/command',
        json={'prompt': 'Open Chrome, go to Gmail, and check whether I have important emails'},
    )

    assert response.status_code == 200
    assert 'event: clarification' in response.text
    assert 'No actions were taken' in response.text
    assert executed == []


def test_app_launch_request_uses_operator_not_legacy_commands(monkeypatch):
    executed = []

    async def available(*args):
        return True

    async def decide(*args):
        return '{"tool":"ask","message":"Waiting for visible Windows Search."}'

    monkeypatch.setattr('app.main.OllamaClient.is_available', available)
    monkeypatch.setattr('app.main.OllamaClient.structured', decide)

    def record_execution(name, params):
        executed.append((name, params))
        return {'ok': True, 'action': name}

    monkeypatch.setattr('app.main.registry.execute', record_execution)
    response = client.post('/api/command', json={'prompt': 'Open Chrome and open https://example.com'})

    assert 'event: clarification' in response.text
    assert executed == []


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


def test_empty_model_decision_is_error(monkeypatch):
    async def answer(*args):
        return ''
    monkeypatch.setattr('app.main.OllamaClient.structured', answer)
    async def available(_self):
        return True

    async def empty_stream(_self, _prompt):
        if False:
            yield ''

    monkeypatch.setattr('app.main.OllamaClient.is_available', available)
    monkeypatch.setattr('app.main.OllamaClient.stream', empty_stream)

    response = client.post('/api/command', json={'prompt': 'What is Wingent?'})
    assert 'event: error' in response.text
    assert 'Invalid JSON' in response.text
    assert 'event: final' not in response.text


def test_clarification_resumes_same_task_without_replaying_accepted_action(monkeypatch):
    from app.capabilities import Arguments
    from app.task_store import TaskStore

    local_registry = ToolRegistry()
    calls = []
    for name in ('first_probe', 'second_probe'):
        local_registry.register(name, 'Controlled probe', ToolPermission.SAFE, {},
                                lambda _, label=name: calls.append(label) or {'ok': True, 'label': label},
                                input_model=Arguments)
    monkeypatch.setattr('app.main.registry', local_registry)
    monkeypatch.setattr('app.main.task_store', TaskStore())

    async def available(_self):
        return True

    async def decide(_self, prompt, _system, _schema):
        context = json.loads(prompt)
        if context.get('selected_tool'):
            return '{}'
        results = context['untrusted_action_results']
        if not results:
            return '{"tool":"first_probe"}'
        if not context['clarification_history']:
            return '{"tool":"ask","message":"Which option should I use?"}'
        assert context['clarification_history'][-1]['answer'] == 'Use option B'
        return '{"tool":"second_probe"}' if len(results) == 1 else '{"tool":"finish"}'

    monkeypatch.setattr('app.main.OllamaClient.is_available', available)
    monkeypatch.setattr('app.main.OllamaClient.structured', decide)

    first = client.post('/api/command', json={'prompt': 'Use two probes, asking for my option between them'})
    assert first.status_code == 200
    clarification = json.loads(first.text.split('event: clarification\ndata: ')[1].split('\n')[0])
    task_id = clarification['resume_task_id']
    assert clarification['attempted'] == 1
    assert calls == ['first_probe']

    second = client.post('/api/command', json={'prompt': 'Use option B', 'resume_task_id': task_id})
    assert second.status_code == 200
    assert '"attempted": 2' in second.text
    assert calls == ['first_probe', 'second_probe']
    assert client.post('/api/command', json={'prompt': 'Again', 'resume_task_id': task_id}).status_code == 409


def test_invalid_resume_id_does_not_start_a_new_task():
    response = client.post('/api/command', json={'prompt': 'Continue', 'resume_task_id': 'a' * 32})
    assert response.status_code == 409


def test_offline_model_does_not_consume_pending_clarification(monkeypatch):
    from app.main import task_store
    from app.task_state import TaskState
    state = TaskState(goal='Inspect a target', criteria=['target checked'], pending_question='Which target?')
    task_store.put(state)
    async def unavailable(_self):
        return False
    monkeypatch.setattr('app.main.OllamaClient.is_available', unavailable)
    response = client.post('/api/command', json={'prompt': 'Target B', 'resume_task_id': state.id})
    assert response.status_code == 503
    assert task_store.take(state.id) is state
    assert state.clarifications == []


def test_model_status_reports_model_problem_to_indicator(monkeypatch):
    async def status(_self, retry=False):
        return {'ready': False, 'code': 'ollama_timeout', 'model': 'local:4b', 'message': 'Ollama is still starting.'}
    monkeypatch.setattr('app.main.OllamaClient.availability', status)
    response = client.get('/api/model-status')
    assert response.status_code == 200
    assert response.json()['ready'] is False
    assert response.json()['code'] == 'ollama_timeout'
