import asyncio
import threading

import pytest

from fastapi.testclient import TestClient

from app.launch_runtime import LaunchAdapter, BudgetedProvider
from app.main import app
from app.capabilities import Arguments
from app.task_state import Action, TaskState
from app.tools import ToolPermission, ToolRegistry


def test_endpoint_reports_unverified_not_complete(monkeypatch):
    monkeypatch.setattr('app.tools.webbrowser.open', lambda *args, **kwargs: True)
    response = TestClient(app).post('/api/command', json={'prompt': 'open github.com'})
    assert '"outcome": "unverified"' in response.text
    assert '"verified": false' in response.text
    assert '"task_id"' in response.text
    assert '"stage": "observing"' in response.text
    assert '"stage": "verifying"' in response.text
    assert TestClient(app).get('/health').json()['runtime'] == 'operator-v13'


def test_oversized_goal_rejected_before_streaming():
    assert TestClient(app).post('/api/command', json={'prompt': 'x' * 4097}).status_code == 422


def test_real_adapter_observes_unavailable_tool_without_faking_page_state(monkeypatch):
    state = TaskState(goal='Open site', criteria=['site visible'])
    adapter = LaunchAdapter([('open_url', {'url': 'https://github.com'})], ToolRegistry(), state, None)
    def unavailable(*args, **kwargs):
        raise ValueError('Browser missing')
    monkeypatch.setattr(adapter.registry, 'validate', unavailable)
    facts = asyncio.run(adapter.observe(state))
    state.observe(facts)
    decision = asyncio.run(adapter.decide(state.context()))
    assert facts['next_ready'] is False
    assert decision.kind == 'ask'
    assert 'no desktop/page visibility' in facts['observation_scope']


def test_changed_precondition_replans_with_real_provider_boundary(monkeypatch):
    class ClarifyProvider:
        async def structured(self, prompt, system, schema):
            assert 'Browser missing' in prompt
            assert 'Original user goal' in prompt
            return '{"disposition":"clarify","message":"Chrome is unavailable. Install it or choose another browser.","steps":[]}'
    state = TaskState(goal='Open Chrome', criteria=['Chrome open'])
    adapter = LaunchAdapter([('open_application', {'application': 'chrome'})], ToolRegistry(), state,
        BudgetedProvider(ClarifyProvider(), state))
    def unavailable(*args, **kwargs):
        raise ValueError('Browser missing')
    monkeypatch.setattr(adapter.registry, 'validate', unavailable)
    state.observe(asyncio.run(adapter.observe(state)))
    decision = asyncio.run(adapter.decide(state.context()))
    assert decision.kind == 'ask'
    assert 'Chrome is unavailable' in decision.message
    assert state.model_calls == 1
    assert state.recoveries == 1


def test_cancelled_execution_invokes_only_its_tool_cancel_hook():
    registry = ToolRegistry()
    started, release = threading.Event(), threading.Event()
    cancelled = []

    def slow(_):
        started.set()
        release.wait(timeout=3)
        return {'ok': True}

    registry.register('slow_fixture', 'Fixture', ToolPermission.SAFE, {}, slow,
                      input_model=Arguments, cancel_task=cancelled.append)
    state = TaskState(goal='Run fixture', criteria=['finished'])
    adapter = LaunchAdapter([], registry, state, None)

    async def scenario():
        task = asyncio.create_task(adapter.execute(Action(tool='slow_fixture', arguments={}, label='slow')))
        await asyncio.to_thread(started.wait, 1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    try:
        asyncio.run(scenario())
    finally:
        release.set()
    assert cancelled == [state.id]
