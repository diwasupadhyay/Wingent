import asyncio

import pytest
from fastapi.testclient import TestClient

from app.capabilities import Arguments
from app.launch_runtime import run_launches
from app.main import app, registry as api_registry
from app.task_state import TaskState
from app.tools import ToolRegistry, ToolPermission


async def connected():
    return False


def setup_registry():
    registry = ToolRegistry()
    calls = []
    registry.register('controlled_action', 'Test-only consequential action', ToolPermission.CONFIRMATION_REQUIRED,
                      {'type': 'object', 'properties': {'target': {'type': 'string'}}, 'required': ['target']},
                      lambda args: calls.append(args) or {'ok': True})
    return registry, calls


@pytest.mark.parametrize('approve', [True, False])
def test_runtime_pauses_for_explicit_response(approve):
    registry, calls = setup_registry()
    events = []
    async def scenario():
        async for name, payload in run_launches([('controlled_action', {'target': 'one'})], registry, connected):
            events.append((name, payload))
            if name == 'confirmation_required':
                assert not calls
                registry.approvals.respond(payload['approval_id'], payload['token'], approve)
    asyncio.run(scenario())
    assert len(calls) == int(approve)
    assert events[-1][0] == ('final' if approve else 'clarification')


def test_each_action_needs_its_own_approval():
    registry, calls = setup_registry()
    approvals = []
    async def scenario():
        async for event, data in run_launches([('controlled_action', {'target': t}) for t in ['one', 'two']], registry, connected):
            if event == 'confirmation_required':
                assert len(calls) == len(approvals)
                approvals.append(data['approval_id'])
                registry.approvals.respond(data['approval_id'], data['token'], True)
    asyncio.run(scenario())
    assert len(set(approvals)) == len(calls) == 2


def test_cancellation_revokes_pending_approval():
    registry, calls = setup_registry()
    async def scenario():
        stream = run_launches([('controlled_action', {'target': 'one'})], registry, connected)
        async for event, data in stream:
            if event == 'confirmation_required':
                await stream.aclose()
                with pytest.raises(PermissionError):
                    registry.approvals.respond(data['approval_id'], data['token'], True)
                break
    asyncio.run(scenario())
    assert not calls


def test_approval_timeout_never_dispatches():
    registry, calls = setup_registry()
    registry.approvals.ttl = 0.01
    async def scenario():
        return [event async for event in run_launches([('controlled_action', {'target': 'one'})], registry, connected)]
    events = asyncio.run(scenario())
    assert not calls
    assert events[-1][0] == 'clarification'


def test_parameter_normalization_change_invalidates_approval():
    registry, calls = setup_registry()
    target = ['one']
    tool = registry.get_tool('controlled_action')
    registry.register(tool.name, tool.description, tool.permission, tool.input_schema, tool.executor,
                      input_model=tool.input_model, precondition=lambda args: {'target': target[0]})
    async def scenario():
        async for event, data in run_launches([('controlled_action', {'target': 'one'})], registry, connected):
            if event == 'confirmation_required':
                registry.approvals.respond(data['approval_id'], data['token'], True)
                target[0] = 'changed'
    asyncio.run(scenario())
    assert not calls


def test_approval_endpoint_requires_token_and_boolean():
    tool = api_registry.get_tool('open_url')
    item = api_registry.approvals.request('test-task', tool.name, tool.revision, {'url': 'https://github.com'})
    client = TestClient(app)
    assert client.post(f'/api/approvals/{item.id}', json={'token': 'wrong', 'approve': True}).status_code == 409
    assert client.post(f'/api/approvals/{item.id}', json={'token': item.token, 'approve': 'yes'}).status_code == 422
    assert client.post(f'/api/approvals/{item.id}', json={'token': item.token, 'approve': False}).status_code == 200
    api_registry.approvals.revoke_task('test-task')


def test_registered_observation_and_verification_hooks_are_used():
    registry = ToolRegistry()
    result = {'value': 0}
    def execute(args):
        result['value'] = 3
        return {'ok': True}
    registry.register('set_value', 'Controlled verification test', ToolPermission.SAFE, {}, execute,
        observe=lambda args: result.copy(),
        verify=lambda args, facts, criteria: {'value is 3': 'Read back 3'} if facts['value'] == 3 else {})
    state = TaskState(goal='Set value', criteria=['value is 3'])
    async def scenario():
        return [event async for event in run_launches([('set_value', {})], registry, connected, state)]
    events = asyncio.run(scenario())
    assert events[-1][1]['verified'] is True
    assert events[-1][1]['evidence'][0]['detail'] == 'Read back 3'


def test_safe_launch_review_uses_the_same_gate(monkeypatch):
    registry = ToolRegistry()
    calls = []
    monkeypatch.setattr('app.tools.webbrowser.open', lambda *args, **kwargs: calls.append(args) or True)
    async def scenario():
        async for event, data in run_launches([('open_url', {'url': 'https://github.com'})], registry, connected, review_actions=True):
            if event == 'confirmation_required':
                assert not calls
                registry.approvals.respond(data['approval_id'], data['token'], False)
    asyncio.run(scenario())
    assert not calls
