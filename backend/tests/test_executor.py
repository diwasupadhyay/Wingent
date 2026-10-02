import asyncio
import json

from fastapi.testclient import TestClient

from app.executor import execute_plan, while_connected
from app.main import app
from app.planner import AgentPlan
from app.routing import detect_deterministic_tools
from app.tools import ToolRegistry


PROMPT = 'can you open chrome and search about genai on youtube and in new tab open github on it'


async def connected():
    return False


def test_exact_user_command_defers_to_planner():
    assert detect_deterministic_tools(PROMPT) == []


def test_endpoint_runs_two_validated_browser_steps(monkeypatch):
    calls = []
    async def available(*args):
        return True
    async def next_action(_self, prompt, system, schema):
        context = json.loads(prompt)
        count = len(context['untrusted_action_results'])
        steps = [
            {'tool': 'search_web', 'arguments': {'engine': 'youtube', 'query': 'genai', 'browser': 'chrome'}},
            {'tool': 'open_url', 'arguments': {'url': 'https://github.com', 'browser': 'chrome'}},
        ]
        if context.get('selected_tool'):
            return json.dumps(steps[count]['arguments'])
        return json.dumps({'tool': steps[count]['tool'] if count < 2 else 'finish'})
    monkeypatch.setattr('app.main.OllamaClient.structured', next_action)
    monkeypatch.setattr('app.main.OllamaClient.is_available', available)
    monkeypatch.setattr('app.tools.resolve_browser', lambda _: 'chrome.exe')
    monkeypatch.setattr('app.tools.subprocess.Popen', lambda args, **kwargs: calls.append(args))
    response = TestClient(app).post('/api/command', json={'prompt': PROMPT})
    assert calls == [
        ['chrome.exe', 'https://www.youtube.com/results?search_query=genai'],
        ['chrome.exe', 'https://github.com'],
    ]
    assert 'event: action' in response.text
    assert response.text.count('"state": "accepted"') == 2
    assert 'event: final' in response.text


def run(actions, registry, disconnected=connected):
    async def collect():
        return [event async for event in execute_plan(actions, registry, disconnected)]
    return asyncio.run(collect())


def test_invalid_later_step_prevents_all_launches(monkeypatch):
    registry = ToolRegistry()
    calls = []
    monkeypatch.setattr(registry, 'execute', lambda *args: calls.append(args))
    events = run([('open_url', {'url': 'https://github.com'}), ('open_application', {'application': 'powershell'})], registry)
    assert calls == []
    assert events[0][0] == 'error'
    assert events[0][1]['code'] == 'invalid_plan'


def test_failure_stops_remaining_steps_and_reports_partial_execution(monkeypatch):
    registry = ToolRegistry()
    calls = []
    def execute(*args):
        calls.append(args)
        if len(calls) == 2:
            raise RuntimeError('Launch rejected')
        return {'ok': True}
    monkeypatch.setattr(registry, 'execute', execute)
    events = run([('open_url', {'url': f'https://github.com/{index}'}) for index in range(3)], registry)
    assert len(calls) == 2
    assert events[-1][1]['code'] == 'partial_execution'
    assert len(events[-1][1]['completed']) == 1


def test_disconnect_between_steps_stops_execution(monkeypatch):
    calls = []
    registry = ToolRegistry()
    monkeypatch.setattr(registry, 'execute', lambda *args: calls.append(args) or {'ok': True})
    async def disconnected():
        return bool(calls)
    run([('open_url', {'url': 'https://github.com'})] * 2, registry, disconnected)
    assert len(calls) == 1


def test_disconnect_cancels_pending_model_call():
    cancelled = []
    async def operation():
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append(True)
    checks = []
    async def disconnected():
        checks.append(True)
        return len(checks) > 1
    async def scenario():
        try:
            await while_connected(operation(), disconnected)
        except asyncio.CancelledError:
            pass
    asyncio.run(scenario())
    assert cancelled == [True]
