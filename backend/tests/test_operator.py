import asyncio
import json

from app.capabilities import Arguments
from app.application_tools import OpenDiscoveredApplication
from app.browser_tools import BrowserLink, BrowserQuery, BrowserUrl
from app.file_tools import FilePath
from app.launch_runtime import BudgetedProvider
from app.operator import OperatorAdapter, run_operator
from app.task_state import Action, ActionRecord, Outcome, TaskState
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


def test_repeated_observations_do_not_evict_discovered_data():
    registry = ToolRegistry()
    state = TaskState(goal='Use the discovered data', criteria=['result'])
    for index in range(5):
        tool = 'discover' if index == 0 else 'reread'
        state.records.append(ActionRecord(action=Action(tool=tool, arguments={}, label=tool),
            outcome=Outcome(status='accepted', summary='Observed',
                            data={'value': 'important-origin' if index == 0 else 'same'}), dispatched=True))
    class Provider:
        async def structured(self, prompt, system, schema):
            context = json.loads(prompt)
            results = context['untrusted_action_results']
            assert [item['result']['value'] for item in results] == ['important-origin', 'same']
            assert context['distinct_results_retained'] == 2
            return '{"tool":"finish"}'
    adapter = OperatorAdapter(registry, state, Provider())
    asyncio.run(adapter.decide(state.context()))


def test_repeated_accepted_write_stops_without_second_dispatch():
    registry = ToolRegistry()
    calls = []
    registry.register('create_artifact', 'Create an artifact', ToolPermission.SAFE, {},
                      lambda p: calls.append(p) or {'ok': True, 'path': p['value']}, input_model=Input)
    class Provider:
        async def structured(self, prompt, system, schema):
            return '{"value":"same"}' if json.loads(prompt).get('selected_tool') else '{"tool":"create_artifact"}'
    state = TaskState(goal='Create an artifact', criteria=['artifact exists'])
    async def run():
        return [event async for event in run_operator(registry, state, BudgetedProvider(Provider(), state), connected)]
    events = asyncio.run(run())
    assert calls == [{'value': 'same'}]
    assert events[-1][0] == 'final'
    assert events[-1][1]['outcome'] == 'unverified'
    assert 'repeats' in events[-1][1]['text']


def test_new_discovery_id_cannot_relaunch_same_app_in_one_task():
    registry = ToolRegistry()
    registry.register('application_open', 'Open discovered app', ToolPermission.CONFIRMATION_REQUIRED,
                      {}, lambda p: {'ok': True}, input_model=OpenDiscoveredApplication)
    path = 'C:/Apps/Fixture.exe'
    older = 'a' * 32
    newer = 'b' * 32
    state = TaskState(goal='Open Fixture', criteria=['Fixture visible'])
    state.records.extend([
        ActionRecord(action=Action(tool='application_open', arguments={'discovery_id': older, 'path': path}, label='open'),
                     outcome=Outcome(status='accepted', summary='Launched', data={'path': path}), dispatched=True),
        ActionRecord(action=Action(tool='application_search', arguments={'query': 'Fixture'}, label='search'),
                     outcome=Outcome(status='accepted', summary='Found', data={'applications': [
                         {'discovery_id': newer, 'path': path, 'name': 'Fixture'}]}), dispatched=True),
    ])
    class Provider:
        async def structured(self, prompt, system, schema):
            if json.loads(prompt).get('selected_tool'):
                return json.dumps({'discovery_id': newer})
            return '{"tool":"application_open"}'
    decision = asyncio.run(OperatorAdapter(registry, state, BudgetedProvider(Provider(), state)).decide(state.context()))
    assert decision.kind == 'finish'
    assert 'already launched' in decision.message


def test_discovery_only_finish_is_challenged_for_open_goal():
    registry = ToolRegistry()
    registry.register('application_open', 'Open discovered app', ToolPermission.CONFIRMATION_REQUIRED,
                      {}, lambda p: {'ok': True}, input_model=OpenDiscoveredApplication)
    state = TaskState(goal='Open Fixture', criteria=['Fixture visible'])
    state.records.append(ActionRecord(
        action=Action(tool='application_search', arguments={'query': 'Fixture'}, label='search'),
        outcome=Outcome(status='accepted', summary='Found', data={'applications': [
            {'discovery_id': 'a' * 32, 'path': 'C:/Apps/Fixture.exe', 'name': 'Fixture'}]}), dispatched=True))
    class Provider:
        async def structured(self, prompt, system, schema):
            if json.loads(prompt).get('selected_tool'):
                return json.dumps({'discovery_id': 'a' * 32})
            return '{"tool":"application_open"}' if 'finish proposal is premature' in system else '{"tool":"finish"}'
    decision = asyncio.run(OperatorAdapter(registry, state, BudgetedProvider(Provider(), state)).decide(state.context()))
    assert decision.kind == 'act'
    assert decision.action.tool == 'application_open'
    assert decision.action.arguments['path'] == 'C:/Apps/Fixture.exe'


def test_empty_application_search_stops_without_invented_launch():
    registry = ToolRegistry()
    state = TaskState(goal='Open MissingScope', criteria=['opened'])
    state.records.append(ActionRecord(
        action=Action(tool='application_search', arguments={'query': 'MissingScope'}, label='search'),
        outcome=Outcome(status='accepted', summary='Searched', data={'applications': []}), dispatched=True))
    class NoProvider:
        async def structured(self, *args):
            raise AssertionError('No model call after a definitive empty indexed search.')
    decision = asyncio.run(OperatorAdapter(registry, state, NoProvider()).decide(state.context()))
    assert decision.kind == 'finish'
    assert 'No matching native application' in decision.message


def test_app_search_query_must_come_from_named_goal():
    from app.application_tools import SearchApplications
    registry = ToolRegistry()
    registry.register('application_search', 'Search apps', ToolPermission.SAFE,
                      {}, lambda p: {'ok': True}, input_model=SearchApplications)
    class Provider:
        async def structured(self, prompt, system, schema):
            if json.loads(prompt).get('selected_tool'):
                return '{"query":"NoteSpace"}' if 'rejected_app_query' in json.loads(prompt) else \
                    '{"query":"Search installed native apps by name"}'
            return '{"tool":"application_search"}'
    state = TaskState(goal='Open NoteSpace', criteria=['opened'])
    decision = asyncio.run(OperatorAdapter(registry, state, BudgetedProvider(Provider(), state)).decide(state.context()))
    assert decision.kind == 'act'
    assert decision.action.arguments['query'] == 'NoteSpace'


def test_unnamed_app_goal_asks_without_guessing_or_model_call():
    registry = ToolRegistry()
    state = TaskState(goal='Open an app for me.', criteria=['app opened'])
    class NoProvider:
        async def structured(self, *args):
            raise AssertionError('The target app is genuinely missing.')
    decision = asyncio.run(OperatorAdapter(registry, state, NoProvider()).decide(state.context()))
    assert decision.kind == 'ask'
    assert 'Which application' in decision.message


def test_invented_local_path_is_rejected_before_dispatch():
    registry = ToolRegistry()
    called = []
    registry.register('list_directory', 'List a local directory', ToolPermission.SAFE, {},
                      lambda p: called.append(p) or {'ok': True}, input_model=FilePath)
    class Provider:
        async def structured(self, prompt, system, schema):
            if json.loads(prompt).get('selected_tool'):
                return '{"path":"/home/user/Desktop/Downloads/Joji.mp3"}'
            return '{"tool":"list_directory"}'
    state = TaskState(goal='Open Chrome and play a Joji song on YouTube', criteria=['song playing'])
    async def run():
        return [event async for event in run_operator(registry, state, BudgetedProvider(Provider(), state), connected)]
    asyncio.run(run())
    assert called == []
    assert not state.records


def test_identical_failed_action_is_not_dispatched_twice():
    registry = ToolRegistry()
    calls = []
    registry.register('try_resource', 'Try a resource', ToolPermission.SAFE, {},
                      lambda p: calls.append(p) or {'ok': False, 'effect': 'no_effect'}, input_model=Input)
    class Provider:
        async def structured(self, prompt, system, schema):
            return '{"value":"missing"}' if json.loads(prompt).get('selected_tool') else '{"tool":"try_resource"}'
    state = TaskState(goal='Try a resource', criteria=['resource found'])
    async def run():
        return [event async for event in run_operator(registry, state, BudgetedProvider(Provider(), state), connected)]
    events = asyncio.run(run())
    assert calls == [{'value': 'missing'}]
    assert events[-1][0] == 'final'
    assert events[-1][1]['outcome'] == 'unverified'
    assert 'repeats' in events[-1][1]['text']


def test_invented_video_id_is_rejected_before_browser_open():
    registry = ToolRegistry()
    calls = []
    registry.register('browser_open', 'Open browser URL', ToolPermission.SAFE, {},
                      lambda p: calls.append(p) or {'ok': True}, input_model=BrowserUrl)
    class Provider:
        async def structured(self, prompt, system, schema):
            if json.loads(prompt).get('selected_tool'):
                return '{"url":"https://www.youtube.com/watch?v=video_id_of_joji_music_video"}'
            return '{"tool":"browser_open"}'
    state = TaskState(goal='Open Chrome and play any Joji music video on YouTube', criteria=['playing'])
    async def run():
        return [event async for event in run_operator(registry, state, BudgetedProvider(Provider(), state), connected)]
    asyncio.run(run())
    assert calls == []
    assert state.records == []


def test_unobserved_browser_link_index_is_rejected_before_dispatch():
    registry = ToolRegistry()
    calls = []
    registry.register('browser_follow_link', 'Follow an observed link', ToolPermission.SAFE, {},
                      lambda p: calls.append(p) or {'ok': True},
                      input_model=BrowserLink)
    class Provider:
        async def structured(self, prompt, system, schema):
            return '{"index":0}' if json.loads(prompt).get('selected_tool') else '{"tool":"browser_follow_link"}'
    state = TaskState(goal='Play a video on YouTube', criteria=['playing'])
    async def run():
        return [event async for event in run_operator(registry, state, BudgetedProvider(Provider(), state), connected)]
    asyncio.run(run())
    assert calls == []


def test_browser_fallback_limitation_is_in_terminal_text():
    registry = ToolRegistry()
    registry.register('browser_search', 'Search in Chrome', ToolPermission.SAFE, {},
                      lambda p: {'ok': True, 'new_window_visible': True,
                                 'page_observed': False, 'browser_control': False,
                                 'limitation': 'Only a Chrome window was observed; playback was not verified.'},
                      input_model=BrowserQuery)
    class Provider:
        async def structured(self, prompt, system, schema):
            context = json.loads(prompt)
            if context.get('selected_tool'):
                return '{"query":"Joji music video","site":"youtube"}'
            return '{"tool":"finish","message":"Done"}' if context['untrusted_action_results'] else '{"tool":"browser_search"}'
    state = TaskState(goal='Play a Joji music video on YouTube', criteria=['playing'])
    async def run():
        return [event async for event in run_operator(registry, state, BudgetedProvider(Provider(), state), connected)]
    events = asyncio.run(run())
    assert events[-1][0] == 'final'
    assert 'playback was not verified' in events[-1][1]['text']


def test_browser_control_failure_stops_before_wasting_model_calls():
    registry = ToolRegistry()
    state = TaskState(goal='Play a song', criteria=['playing'])
    state.records.append(ActionRecord(action=Action(tool='browser_search', arguments={}, label='search'),
        outcome=Outcome(status='accepted', summary='Window opened', data={
            'browser_control': False, 'new_window_visible': True,
            'limitation': 'The page and playback were not observed.'}), dispatched=True))
    class NoProvider:
        async def structured(self, *args):
            raise AssertionError('No more model calls when the browser cannot be controlled.')
    decision = asyncio.run(OperatorAdapter(registry, state, NoProvider()).decide(state.context()))
    assert decision.kind == 'finish'
    assert 'cannot select a result' in decision.message


def test_search_page_cannot_be_reopened_instead_of_following_an_observed_link():
    registry = ToolRegistry()
    opened = []
    registry.register('browser_open', 'Navigate browser', ToolPermission.SAFE, {},
                      lambda p: opened.append(p) or {'ok': True}, input_model=BrowserUrl)
    registry.register('browser_follow_link', 'Follow observed link', ToolPermission.SAFE, {},
                      lambda p: opened.append(p) or {'ok': True}, input_model=BrowserLink)
    state = TaskState(goal='Play 777 by Joji', criteria=['777 playing'])
    state.records.append(ActionRecord(
        action=Action(tool='browser_search', arguments={'query': 'Joji 777'}, label='search'),
        outcome=Outcome(status='accepted', summary='Observed', data={
            'page_observed': True, 'url': 'https://www.youtube.com/results?search_query=Joji+777',
            'links': [{'index': 1, 'text': 'Joji - 777',
                       'url': 'https://www.youtube.com/watch?v=observed'}], 'media': []}),
        dispatched=True))
    class Provider:
        async def structured(self, prompt, system, schema):
            context = json.loads(prompt)
            if context.get('selected_tool') == 'browser_open':
                return '{"url":"https://www.youtube.com/results?search_query=Joji+777"}'
            if context.get('selected_tool') == 'browser_follow_link':
                return '{"index":1}'
            return '{"tool":"browser_follow_link"}' if context.get('rejected_navigation') else '{"tool":"browser_open"}'
    decision = asyncio.run(OperatorAdapter(registry, state, BudgetedProvider(Provider(), state)).decide(state.context()))
    assert decision.action.tool == 'browser_follow_link'
    assert decision.action.arguments == {'index': 1}
    assert not opened


def test_play_is_not_dispatched_on_observed_page_without_media():
    registry = ToolRegistry()
    calls = []
    registry.register('browser_play_media', 'Play media', ToolPermission.SAFE, {},
                      lambda _: calls.append('played') or {'ok': True}, input_model=Arguments)
    registry.register('browser_follow_link', 'Follow link', ToolPermission.SAFE, {},
                      lambda p: calls.append(p) or {'ok': True}, input_model=BrowserLink)
    state = TaskState(goal='Play observed media', criteria=['playing'])
    state.records.append(ActionRecord(action=Action(tool='browser_search', arguments={}, label='search'),
        outcome=Outcome(status='accepted', summary='Observed', data={
            'page_observed': True, 'url': 'https://example.com/results',
            'links': [{'index': 0, 'url': 'https://example.com/watch', 'text': 'Result'}],
            'media': []}), dispatched=True))
    class Provider:
        async def structured(self, prompt, system, schema):
            context = json.loads(prompt)
            if context.get('selected_tool') == 'browser_follow_link':
                return '{"index":0}'
            if context.get('selected_tool') == 'browser_play_media':
                return '{}'
            return '{"tool":"browser_follow_link"}' if context.get('rejected_play') else '{"tool":"browser_play_media"}'
    decision = asyncio.run(OperatorAdapter(registry, state, BudgetedProvider(Provider(), state)).decide(state.context()))
    assert decision.action.tool == 'browser_follow_link'
    assert not calls


def test_reasoning_budget_stops_with_partial_results_without_another_model_call():
    registry = ToolRegistry()
    state = TaskState(goal='Continue task', criteria=['goal complete'])
    state.records.append(ActionRecord(action=Action(tool='open_url', arguments={'url':'https://example.com'}, label='open'),
        outcome=Outcome(status='accepted', summary='Accepted'), dispatched=True))
    state.model_calls = state.limits.model_calls
    class NoProvider:
        async def structured(self, *args):
            raise AssertionError('The exhausted model must not be called.')
    decision = asyncio.run(OperatorAdapter(registry, state, NoProvider()).decide(state.context()))
    assert decision.kind == 'finish' and 'budget' in decision.message


def test_duplicate_feedback_changes_next_action_before_dispatch():
    registry = ToolRegistry()
    registry.register('inspect_item', 'Inspect an item', ToolPermission.SAFE, {},
                      lambda _: {'ok': True, 'value': 'observed'}, input_model=Arguments)
    registry.register('produce_item', 'Produce an item', ToolPermission.SAFE, {},
                      lambda _: {'ok': True}, input_model=Arguments)
    state = TaskState(goal='Inspect and produce', criteria=['item produced'])
    state.records.append(ActionRecord(action=Action(tool='inspect_item', arguments={}, label='inspect'),
        outcome=Outcome(status='accepted', summary='Observed', data={'value': 'observed'}), dispatched=True))
    class Provider:
        async def structured(self, prompt, system, schema):
            context = json.loads(prompt)
            if context.get('selected_tool'):
                return '{}'
            return '{"tool":"produce_item"}' if context.get('rejected_repeat') else '{"tool":"inspect_item"}'
    decision = asyncio.run(OperatorAdapter(registry, state, BudgetedProvider(Provider(), state)).decide(state.context()))
    assert decision.kind == 'act' and decision.action.tool == 'produce_item'
    assert len(state.records) == 1
