import asyncio
import json

import pytest
from pydantic import Field, ValidationError

from app.capabilities import Arguments, Capability
from app.capability_planner import plan_request, plan_model, compile_plan
from app.tools import ToolRegistry, ToolPermission


class CountInput(Arguments):
    count: int = Field(ge=1, le=3)


def test_new_typed_tool_is_available_without_changing_planner():
    registry = ToolRegistry()
    registry.capabilities['example'] = Capability('example', 'A controlled test capability.')
    registry.register('count_items', 'Count items', ToolPermission.SAFE, {}, lambda args: {'ok': True},
                      input_model=CountInput, capability='example')
    class Provider:
        async def structured(self, prompt, system, schema):
            assert 'count_items' in json.dumps(schema)
            assert 'controlled test capability' in system
            return '{"disposition":"execute","message":"","steps":[{"tool":"count_items","arguments":{"count":2}}]}'
    plan = asyncio.run(plan_request('Count two items', Provider(), registry))
    assert compile_plan(plan) == [('count_items', {'count': 2})]


@pytest.mark.parametrize('value', ['2', True, 0, 4])
def test_typed_inputs_fail_closed(value):
    registry = ToolRegistry()
    registry.register('count', 'Count', ToolPermission.SAFE, {}, lambda args: {'ok': True}, input_model=CountInput)
    with pytest.raises(ValidationError):
        registry.prepare('count', {'count': value})


def test_model_cannot_generate_approval_fields_or_restricted_tools():
    registry = ToolRegistry()
    registry.register('shell', 'Restricted', ToolPermission.RESTRICTED, {}, lambda _: {'ok': True})
    model = plan_model(registry)
    assert 'shell' not in json.dumps(model.model_json_schema())
    for step in [
        {'tool': 'shell', 'arguments': {}},
        {'tool': 'open_url', 'arguments': {'url': 'https://github.com', 'confirmed': True}},
        {'tool': 'open_url', 'arguments': {'url': 'https://github.com'}, 'approval_id': 'fake'},
    ]:
        with pytest.raises(ValidationError):
            model.model_validate({'disposition': 'execute', 'message': '', 'steps': [step]})


def test_output_contract_is_validated_after_tool_call():
    registry = ToolRegistry()
    registry.register('broken', 'Broken', ToolPermission.SAFE, {}, lambda _: {'ok': 'yes'})
    with pytest.raises(ValidationError):
        registry.execute('broken')


def test_metadata_exposes_limits_but_no_execution_authority():
    manifest = ToolRegistry().manifest()
    assert all(item['timeout_seconds'] > 0 and not item['retry_safe'] for item in manifest)
    assert all('executor' not in item and 'input_schema' in item and 'output_schema' in item for item in manifest)


def test_registry_requires_bound_approval_and_never_boolean_bypass():
    registry = ToolRegistry()
    calls = []
    registry.register('consequential', 'Test', ToolPermission.CONFIRMATION_REQUIRED, {}, lambda _: calls.append(True) or {'ok': True})
    registry.prepare('consequential', {})
    with pytest.raises(PermissionError):
        registry.execute('consequential')
    with pytest.raises(TypeError):
        registry.execute('consequential', confirmed=True)
    tool = registry.get_tool('consequential')
    item = registry.approvals.request('task', tool.name, tool.revision, {})
    registry.approvals.respond(item.id, item.token, True)
    registry.execute(tool.name, approval_id=item.id, task_id='task')
    assert calls == [True]


def test_explicit_destination_omission_is_rejected_before_execution():
    class Provider:
        async def structured(self, prompt, system, schema):
            return '{"disposition":"execute","message":"","steps":[{"tool":"open_url","arguments":{"url":"https://www.youtube.com"}}]}'
    with pytest.raises(ValueError, match='omitted explicit'):
        asyncio.run(plan_request('open github.com in another tab', Provider()))


def test_restricted_tool_cannot_be_approved():
    registry = ToolRegistry()
    calls = []
    registry.register('restricted', 'Restricted', ToolPermission.RESTRICTED, {}, lambda _: calls.append(True) or {'ok': True})
    tool = registry.get_tool('restricted')
    item = registry.approvals.request('task', tool.name, tool.revision, {})
    registry.approvals.respond(item.id, item.token, True)
    with pytest.raises(PermissionError, match='restricted'):
        registry.execute(tool.name, task_id='task', approval_id=item.id)
    assert not calls


def test_tool_replacement_invalidates_existing_approval():
    registry = ToolRegistry()
    calls = []
    def register():
        registry.register('guarded', 'Guarded', ToolPermission.CONFIRMATION_REQUIRED, {}, lambda _: calls.append(True) or {'ok': True})
    register()
    tool = registry.get_tool('guarded')
    item = registry.approvals.request('task', tool.name, tool.revision, {})
    registry.approvals.respond(item.id, item.token, True)
    register()
    with pytest.raises(PermissionError):
        registry.execute('guarded', task_id='task', approval_id=item.id)
    assert not calls
