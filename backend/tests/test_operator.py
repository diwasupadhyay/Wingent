import asyncio
import json

from app.capabilities import Arguments
from app.launch_runtime import BudgetedProvider
from app.operator import run_operator
from app.task_state import TaskState
from app.tools import ToolRegistry, ToolPermission


class Input(Arguments):
    value: str


async def connected():
    return False


def test_discovers_then_uses_result_without_fixed_plan():
    registry = ToolRegistry()
    calls = []
    registry.register('discover', 'Discover a resource', ToolPermission.SAFE, {},
                      lambda p: {'ok': True, 'resource': 'observed-42'}, input_model=Arguments)
    registry.register('inspect_resource', 'Inspect discovered resource', ToolPermission.SAFE, {},
                      lambda p: calls.append(p) or {'ok': True, 'value': 'ready'}, input_model=Input)
    class Provider:
        async def structured(self, prompt, system, schema):
            context = json.loads(prompt)
            results = context['untrusted_action_results']
            if context.get('selected_tool') == 'discover':
                return '{}'
            if context.get('selected_tool') == 'inspect_resource':
                return json.dumps({'value': results[0]['result']['resource']})
            if not results:
                return '{"tool":"discover"}'
            if len(results) == 1:
                return '{"tool":"inspect_resource"}'
            return '{"tool":"finish","message":"Inspected the discovered resource."}'
    state = TaskState(goal='Inspect the available resource', criteria=['resource inspected'])
    async def run():
        return [e async for e in run_operator(registry, state, BudgetedProvider(Provider(), state), connected)]
    events = asyncio.run(run())
    assert calls == [{'value': 'observed-42'}]
    assert state.model_calls == 5
    assert events[-1][1]['verified'] is False


def test_replans_after_known_no_effect_and_keeps_original_goal():
    registry = ToolRegistry()
    registry.register('attempt', 'Try resource', ToolPermission.SAFE, {},
                      lambda p: {'ok': p['value'] == 'new', 'effect': 'no_effect', 'found': 'new'}, input_model=Input)
    class Provider:
        async def structured(self, prompt, system, schema):
            context = json.loads(prompt)
            assert context['original_goal'] == 'Inspect resource'
            records = context['untrusted_action_results']
            if len(records) == 2:
                return '{"tool":"finish"}'
            value = records[-1]['result']['found'] if records else 'old'
            return json.dumps({'value': value}) if context.get('selected_tool') else '{"tool":"attempt"}'
    state = TaskState(goal='Inspect resource', criteria=['inspected'])
    async def run():
        return [e async for e in run_operator(registry, state, BudgetedProvider(Provider(), state), connected)]
    asyncio.run(run())
    assert [r.action.arguments['value'] for r in state.records] == ['old', 'new']
    assert state.recoveries == 1
