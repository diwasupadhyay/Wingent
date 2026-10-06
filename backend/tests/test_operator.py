import asyncio
import pytest
import json
from types import SimpleNamespace

from app.capabilities import Arguments
from app.application_tools import OpenDiscoveredApplication
from app.browser_tools import BrowserLink, BrowserQuery, BrowserUrl
from app.file_tools import FilePath
from app.launch_runtime import BudgetedProvider
from app.operator import OperatorAdapter, run_operator
from app.task_state import Action, ActionRecord, Outcome, TaskState
from app.tools import ToolRegistry, ToolPermission
from app.working_context import observed_effects


def test_packaged_app_grant_uses_unique_observed_title_not_explorer_pid():
    from app.operator import _ground_window_grant
    launch = ActionRecord(action=Action(tool='application_open', arguments={}, label='Open'),
        outcome=Outcome(status='accepted', summary='Launched', data={'application': 'Calculator',
            'pid': 900, 'path': r'shell:AppsFolder\Microsoft.WindowsCalculator!App'}), dispatched=True)
    window = {'window_id': 42, 'pid': 123, 'title': 'Calculator', 'process': 'CalculatorApp.exe'}
    observed = ActionRecord(action=Action(tool='observe_windows', arguments={}, label='Observe'),
        outcome=Outcome(status='accepted', summary='Seen', data={'windows': [window,
            {'window_id': 99, 'pid': 900, 'title': 'Documents', 'process': 'explorer.exe'}]}), dispatched=True)
    assert _ground_window_grant({}, [launch, observed], 'Calculate')['window_id'] == 42
    observed.outcome.data['windows'].append({**window, 'window_id': 43})
    assert 'window_id' not in _ground_window_grant({}, [launch, observed], 'Calculate')


def test_active_control_is_not_regranted_instead_of_input():
    from app.computer_tools import BeginControl, ComputerAction
    registry = ToolRegistry()
    registry.register('observe_windows', 'Observe', ToolPermission.SAFE, {}, lambda p: {}, input_model=Arguments)
    registry.register('computer_begin', 'Begin', ToolPermission.SAFE, {}, lambda p: {}, input_model=BeginControl)
    registry.register('computer_action', 'Input', ToolPermission.SAFE, {}, lambda p: {}, input_model=ComputerAction)
    registry.computer_session = SimpleNamespace(visual_context=lambda _: {
        'window_id': 42, 'frame_id': 'fresh', 'scope': 'window', 'input_targeted': True, 'image': b'pixels'})
    state = TaskState(goal='Calculate', criteria=['Result'])
    calls = []
    class Provider:
        async def structured_images(self, *args):
            calls.append(1)
            return json.dumps({'tool': 'computer_begin', 'arguments': {'window_id': 42, 'purpose': 'Calculate'}}) if len(calls) == 1 else json.dumps({
                'tool': 'computer_action', 'arguments': {'frame_id': 'fresh', 'kind': 'type', 'text': '247*38'}})
    decision = asyncio.run(OperatorAdapter(registry, state, BudgetedProvider(Provider(), state)).decide(state.context()))
    assert decision.action.tool == 'computer_action'
    assert len(calls) == 2


@pytest.mark.parametrize('visible, expected', [(True, True), (False, False)])
def test_typing_goal_requires_exact_observed_editable_text(visible, expected):
    state = TaskState(goal='Open Notepad and type: Wingent can see, think, and act.', criteria=['Text entered'])
    state.records.append(ActionRecord(action=Action(tool='computer_action', label='type',
        arguments={'kind': 'type', 'text': 'Wingent can see, think, and act.'}), dispatched=True,
        outcome=Outcome(status='accepted', summary='Input sent', data={'post_observation': {
            'ok': True, 'title': 'Untitled - Notepad', 'controls': [{'role': 'ControlType.Document',
                'value': 'Wingent can see, think, and act.' if visible else ''}]}})))
    adapter = OperatorAdapter(ToolRegistry(), state, None)
    observation = state.observe({'results': []})
    report = asyncio.run(adapter.verify(state, observation))
    assert state.verified_by(report, observation) is expected


def test_focus_pause_preserves_task_for_resume_without_replaying_input():
    from app.computer_tools import BeginControl, ObserveComputer
    registry = ToolRegistry()
    registry.tools.clear()
    closed = []
    registry.computer_session = SimpleNamespace(visual_context=lambda owner: None,
                                                close_task=lambda owner: closed.append(owner))
    registry.register('computer_begin', 'Grant a window', ToolPermission.SAFE, {},
                      lambda p: {'ok': True, 'frame_id': 'new'}, input_model=BeginControl)
    registry.register('computer_observe', 'Observe a window', ToolPermission.SAFE, {},
                      lambda p: {'ok': False, 'effect': 'no_effect',
                                 'reason': 'Windows did not grant focus', 'needs_user_attention': True},
                      input_model=ObserveComputer)
    state = TaskState(goal='Inspect the window', criteria=['Window inspected'])
    prior = Action(tool='computer_begin', arguments={'window_id': 1, 'purpose': 'Inspect the window'}, label='Grant window')
    state.records.append(ActionRecord(action=prior, outcome=Outcome(status='accepted', summary='Granted'), dispatched=True))
    class Provider:
        async def structured(self, prompt, system, schema):
            if json.loads(prompt)['clarification_history']:
                return '{"tool":"computer_begin","arguments":{"window_id":1,"purpose":"Inspect the window"}}'
            return '{"tool":"computer_observe","arguments":{"window_id":1}}'
    async def run():
        return [event async for event in run_operator(registry, state, BudgetedProvider(Provider(), state), connected)]
    events = asyncio.run(run())
    assert events[-1][0] == 'clarification'
    assert events[-1][1]['resume_task_id'] == state.id
    assert state.recoveries == 0 and len(state.records) == 2
    assert closed == [state.id]
    state.resume('ready')
    decision = asyncio.run(OperatorAdapter(registry, state, BudgetedProvider(Provider(), state)).decide(state.context()))
    assert decision.kind == 'act' and decision.action.tool == 'computer_begin'


def test_app_launch_hands_off_to_window_observation_without_model_call():
    registry = ToolRegistry()
    registry.register('observe_windows', 'See actual windows', ToolPermission.SAFE, {},
                      lambda _: {'ok': True, 'windows': []}, input_model=Arguments)
    state = TaskState(goal='Open an app and type', criteria=['Text visible'])
    state.records.append(ActionRecord(action=Action(tool='open_application',
        arguments={'application': 'notepad'}, label='Launch'),
        outcome=Outcome(status='accepted', summary='Launched', data={'pid': 42}), dispatched=True))
    class Provider:
        async def structured(self, prompt, system, schema):
            raise AssertionError('Window observation should not need a model call')
    decision = asyncio.run(OperatorAdapter(registry, state, BudgetedProvider(Provider(), state)).decide(state.context()))
    assert decision.kind == 'act' and decision.action.tool == 'observe_windows'
    assert state.model_calls == 0


def test_computer_grant_rejects_unobserved_window_id():
    from app.computer_tools import BeginControl
    registry = ToolRegistry()
    registry.tools.clear()
    registry.register('observe_windows', 'See windows', ToolPermission.SAFE, {},
                      lambda _: {'ok': True}, input_model=Arguments)
    registry.register('computer_begin', 'Grant observed window', ToolPermission.CONFIRMATION_REQUIRED, {},
                      lambda _: {'ok': True}, input_model=BeginControl)
    registry.computer_session = SimpleNamespace(visual_context=lambda owner: None)
    state = TaskState(goal='Type in the open app', criteria=['Text visible'])
    state.records.append(ActionRecord(action=Action(tool='observe_windows', arguments={}, label='Observe'),
        outcome=Outcome(status='accepted', summary='Windows', data={'windows': [{'window_id': 7}]}), dispatched=True))
    calls = []
    class Provider:
        async def structured(self, prompt, system, schema):
            calls.append(system)
            window_id = 999 if len(calls) == 1 else 7
            return json.dumps({'tool': 'computer_begin', 'arguments': {
                'window_id': window_id, 'purpose': 'Type in the open app'}})
    decision = asyncio.run(OperatorAdapter(registry, state, BudgetedProvider(Provider(), state)).decide(state.context()))
    assert decision.kind == 'act' and decision.action.arguments['window_id'] == 7
    assert len(calls) == 2 and 'NOT attempted' in calls[1]


def test_unique_launched_window_fills_grant_without_extra_model_call():
    from app.computer_tools import BeginControl
    registry = ToolRegistry()
    registry.tools.clear()
    registry.register('observe_windows', 'See windows', ToolPermission.SAFE, {},
                      lambda _: {'ok': True}, input_model=Arguments)
    registry.register('computer_begin', 'Grant observed window', ToolPermission.CONFIRMATION_REQUIRED, {},
                      lambda _: {'ok': True}, input_model=BeginControl)
    registry.computer_session = SimpleNamespace(visual_context=lambda owner: None)
    state = TaskState(goal='Type a quote in the app', criteria=['Quote visible'])
    state.records.extend([
        ActionRecord(action=Action(tool='open_application', arguments={'application': 'notepad'}, label='Open'),
                     outcome=Outcome(status='accepted', summary='Launched', data={'pid': 42}), dispatched=True),
        ActionRecord(action=Action(tool='observe_windows', arguments={}, label='See windows'),
                     outcome=Outcome(status='accepted', summary='Observed', data={'windows': [
                         {'window_id': 7, 'pid': 42, 'title': 'Untitled', 'process': 'notepad.exe'},
                         {'window_id': 8, 'pid': 99, 'title': 'Other', 'process': 'other.exe'}]}), dispatched=True),
    ])
    calls = []
    class Provider:
        async def structured(self, prompt, system, schema):
            calls.append(prompt)
            return '{"tool":"computer_begin"}'
    decision = asyncio.run(OperatorAdapter(registry, state, BudgetedProvider(Provider(), state)).decide(state.context()))
    assert decision.kind == 'act'
    assert decision.action.arguments == {'window_id': 7, 'purpose': state.goal, 'scope': 'window',
                                         'window_title': 'Untitled', 'process': 'notepad.exe'}
    assert len(calls) == 0  # Unique observed handoff needs no inference.


def test_ambiguous_launched_windows_are_not_chosen_by_host():
    from app.operator import _ground_window_grant
    records = [
        ActionRecord(action=Action(tool='application_open', arguments={}, label='Open'),
                     outcome=Outcome(status='accepted', summary='Launched', data={'pid': 42}), dispatched=True),
        ActionRecord(action=Action(tool='observe_windows', arguments={}, label='Observe'),
                     outcome=Outcome(status='accepted', summary='Windows', data={'windows': [
                         {'window_id': 7, 'pid': 42}, {'window_id': 8, 'pid': 42}]}), dispatched=True),
    ]
    assert _ground_window_grant({}, records, 'Use app') == {'purpose': 'Use app'}


def test_final_result_includes_last_failed_action_reason():
    registry = ToolRegistry()
    state = TaskState(goal='Use the window', criteria=['Window changed'])
    state.records.append(ActionRecord(action=Action(tool='computer_begin', arguments={}, label='Grant'),
        outcome=Outcome(status='no_effect', summary='Application identity changed.'), dispatched=False))
    class Provider:
        async def structured(self, prompt, system, schema):
            return '{"tool":"finish","message":"Cannot continue."}'
    events = asyncio.run(_collect_run(registry, state, Provider()))
    assert events[-1][0] == 'final'
    assert 'computer_begin: Application identity changed.' in events[-1][1]['text']


def test_brain_replans_untargeted_typing_before_dispatch():
    from app.computer_tools import ComputerAction
    registry = ToolRegistry()
    registry.tools.clear()
    registry.register('computer_action', 'Input in the granted window', ToolPermission.SAFE, {},
                      lambda p: {'ok': True}, input_model=ComputerAction)
    registry.computer_session = SimpleNamespace(visual_context=lambda owner: {
        'frame_id': 'current', 'input_targeted': False, 'image': b'pixels'})
    calls = []
    class Provider:
        async def structured_images(self, prompt, system, schema, images):
            calls.append(system)
            if len(calls) == 1:
                return '{"tool":"computer_action","arguments":{"frame_id":"current","kind":"type","text":"Hello"}}'
            return '{"tool":"computer_action","arguments":{"frame_id":"current","kind":"click","x":500,"y":300}}'
    state = TaskState(goal='Enter Hello in the open app', criteria=['Hello entered'])
    decision = asyncio.run(OperatorAdapter(registry, state, BudgetedProvider(Provider(), state)).decide(state.context()))
    assert decision.action.arguments['kind'] == 'click'
    assert len(calls) == 2 and 'NOT dispatched' in calls[1]
    assert not state.records


def test_host_effect_ledger_distinguishes_dispatch_from_verified_artifact():
    state = TaskState(goal='Create a report and complete the task', criteria=['Task complete'])
    state.records.extend([
        ActionRecord(action=Action(tool='computer_action', arguments={}, label='Click'),
                     outcome=Outcome(status='accepted', summary='Sent', data={
                         'post_observation': {'ok': True}, 'visible_change_observed': False,
                         'verified': True}), dispatched=True),
        ActionRecord(action=Action(tool='create_text', arguments={}, label='Write'),
                     outcome=Outcome(status='accepted', summary='Written', data={
                         'content_matches': True, 'path': 'D:/test/report.txt'}), dispatched=True),
    ])
    facts = observed_effects(state)
    assert 'visible change not detected' in facts[0]['detail']
    assert 'matching bytes' in facts[1]['detail']
    assert all('Task complete' not in item['detail'] for item in facts)


@pytest.mark.parametrize('changed_window', [False, True])
def test_repeated_computer_click_is_reconsidered_after_visible_change(changed_window):
    from app.computer_tools import ComputerAction
    registry = ToolRegistry()
    registry.tools.clear()
    registry.register('computer_action', 'One window input', ToolPermission.SAFE, {},
                      lambda p: {'ok': True}, input_model=ComputerAction)
    registry.register('computer_confirm_action', 'Approved window input', ToolPermission.CONFIRMATION_REQUIRED, {},
                      lambda p: {'ok': True}, input_model=ComputerAction)
    registry.computer_session = SimpleNamespace(visual_context=lambda owner: {
        'frame_id': 'current', 'window_id': 2 if changed_window else 1, 'input_targeted': True, 'image': b'pixels'})
    state = TaskState(goal='Apply the visible change', criteria=['Applied'])
    state.records.append(ActionRecord(
        action=Action(tool='computer_action', arguments={'frame_id': 'old', 'kind': 'click', 'x': 500, 'y': 550}, label='Click'),
        outcome=Outcome(status='accepted', summary='Sent', data={'visible_change_observed': True,
                        'action_window_id': 1, 'post_observation': {'window_id': 2}}), dispatched=True))
    calls = []
    class Provider:
        async def structured_images(self, prompt, system, schema, images):
            calls.append(system)
            if len(calls) == 1:
                return '{"tool":"computer_confirm_action","arguments":{"frame_id":"current","kind":"click","x":500,"y":550}}'
            return '{"tool":"finish","message":"The requested change is visible."}'
    decision = asyncio.run(OperatorAdapter(registry, state, BudgetedProvider(Provider(), state)).decide(state.context()))
    assert decision.kind == ('act' if changed_window else 'finish')
    assert len(calls) == (1 if changed_window else 2)
    if not changed_window:
        assert 'requested change is visible' in decision.message
    assert len(state.records) == 1


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
    assert state.model_calls == 4  # Empty-input discovery needs no separate argument generation.
    assert events[-1][1]['verified'] is False


def test_one_model_call_can_choose_and_fill_tool_arguments():
    registry = ToolRegistry()
    registry.register('inspect_resource', 'Inspect a named resource', ToolPermission.SAFE, {},
                      lambda p: {'ok': True, 'value': p['value']}, input_model=Input)
    calls = []
    class Provider:
        async def structured(self, prompt, system, schema):
            calls.append((json.loads(prompt), system))
            return '{"tool":"inspect_resource","arguments":{"value":"alpha"},"objective":"Inspect alpha"}'
    state = TaskState(goal='Inspect alpha', criteria=['alpha inspected'])
    decision = asyncio.run(OperatorAdapter(registry, state, BudgetedProvider(Provider(), state)).decide(state.context()))
    assert decision.kind == 'act' and decision.action.arguments == {'value': 'alpha'}
    assert decision.message == 'Inspect alpha'
    assert state.model_calls == 1 and len(calls) == 1
    assert calls[0][0]['original_goal'] == 'Inspect alpha'
    assert 'Tool guidance: []' in calls[0][1]


def test_invalid_combined_arguments_use_typed_repair():
    registry = ToolRegistry()
    registry.register('inspect_resource', 'Inspect a named resource', ToolPermission.SAFE, {},
                      lambda p: {'ok': True}, input_model=Input)
    calls = []
    class Provider:
        async def structured(self, prompt, system, schema):
            calls.append(json.loads(prompt))
            return '{"value":"alpha"}' if calls[-1].get('selected_tool') else '{"tool":"inspect_resource","arguments":{"bad":"alpha"}}'
    state = TaskState(goal='Inspect alpha', criteria=['alpha inspected'])
    decision = asyncio.run(OperatorAdapter(registry, state, BudgetedProvider(Provider(), state)).decide(state.context()))
    assert decision.kind == 'act' and decision.action.arguments == {'value': 'alpha'}
    assert state.model_calls == 2


def test_flexible_media_goal_searches_observed_result_then_checks_playback():
    from app.browser_tools import register as register_browser
    class Browser:
        def __init__(self):
            self.calls = []
        def search(self, query, site='youtube'):
            self.calls.append(('search', query))
            return {'ok': True, 'url': 'https://www.youtube.com/results?search_query=joji',
                    'links': [{'index': 0, 'text': 'Joji - Song A',
                               'url': 'https://www.youtube.com/watch?v=observed'}],
                    'media': [], 'page_observed': True}
        def follow(self, index):
            self.calls.append(('follow', index))
            return {'ok': True, 'url': 'https://www.youtube.com/watch?v=observed',
                    'title': 'Joji - Song A', 'links': [],
                    'media': [{'paused': True, 'current_time': 0}], 'page_observed': True}
        def play_media(self):
            self.calls.append(('play',))
            return {'ok': True, 'url': 'https://www.youtube.com/watch?v=observed',
                    'title': 'Joji - Song A', 'media': {'paused': False, 'current_time': 2.1},
                    'page_observed': True, 'playback_progressed': True}
    browser = Browser()
    registry = ToolRegistry()
    register_browser(registry, browser)
    class Provider:
        async def structured(self, prompt, system, schema):
            results = json.loads(prompt)['untrusted_action_results']
            if not results:
                return '{"tool":"browser_search","arguments":{"query":"Joji song","site":"youtube"}}'
            if results[-1]['tool'] == 'browser_search':
                return '{"tool":"browser_follow_link","arguments":{"index":0}}'
            if results[-1]['tool'] == 'browser_follow_link':
                return '{"tool":"browser_play_media","arguments":{}}'
            return '{"tool":"finish","message":"Observed the video playing."}'
    state = TaskState(goal='Open Chrome and play any Joji song on YouTube', criteria=['Joji song playing'])
    events = asyncio.run(_collect_run(registry, state, Provider()))
    assert browser.calls == [('search', 'Joji song'), ('follow', 0), ('play',)]
    assert state.model_calls == 3
    assert events[-1][0] == 'final' and events[-1][1]['verified'] is False
    assert 'HTML media time advanced' in events[-1][1]['text']


def test_search_only_finish_cannot_claim_playback():
    registry = ToolRegistry()
    state = TaskState(goal='Play any song by an artist on a video site', criteria=['music playing'])
    state.records.append(ActionRecord(
        action=Action(tool='browser_search', arguments={'query': 'artist song'}, label='search'),
        outcome=Outcome(status='accepted', summary='Observed results', data={
            'page_observed': True, 'url': 'https://example.com/results',
            'links': [{'index': 0, 'text': 'Artist - Song', 'url': 'https://example.com/video'}],
            'media': []}), dispatched=True))
    class Provider:
        async def structured(self, prompt, system, schema):
            return '{"tool":"finish","message":"Done"}'
    events = asyncio.run(_collect_run(registry, state, Provider()))
    assert events[-1][0] == 'final'
    assert 'remains unfinished' in events[-1][1]['text']
    assert state.model_calls == 2


def test_observed_selected_media_can_trigger_play_without_model_call():
    registry = ToolRegistry()
    registry.register('browser_play_media', 'Play observed media', ToolPermission.SAFE, {},
                      lambda _: {'ok': True}, input_model=Arguments)
    state = TaskState(goal='Watch any relevant music video', criteria=['video playing'])
    state.records.append(ActionRecord(
        action=Action(tool='browser_follow_link', arguments={'index': 0}, label='follow'),
        outcome=Outcome(status='accepted', summary='Observed selected page', data={
            'page_observed': True, 'title': 'Relevant video',
            'media': [{'paused': True, 'current_time': 0}]}), dispatched=True))
    state.model_calls = state.limits.model_calls
    class NoProvider:
        async def structured(self, *args):
            raise AssertionError('An observed paused media postcondition needs no model call.')
    decision = asyncio.run(OperatorAdapter(registry, state, NoProvider()).decide(state.context()))
    assert decision.kind == 'act' and decision.action.tool == 'browser_play_media'
    assert decision.action.arguments == {}


def test_negative_playback_request_does_not_trigger_play():
    registry = ToolRegistry()
    registry.register('browser_play_media', 'Play observed media', ToolPermission.SAFE, {},
                      lambda _: {'ok': True}, input_model=Arguments)
    state = TaskState(goal='Find a video but do not play it', criteria=['video found'])
    state.records.append(ActionRecord(
        action=Action(tool='browser_follow_link', arguments={'index': 0}, label='follow'),
        outcome=Outcome(status='accepted', summary='Observed selected page', data={
            'page_observed': True, 'title': 'Video', 'media': [{'paused': True}]}), dispatched=True))
    class Provider:
        async def structured(self, *args):
            return '{"tool":"finish","message":"Found the video without playing it."}'
    decision = asyncio.run(OperatorAdapter(registry, state, BudgetedProvider(Provider(), state)).decide(state.context()))
    assert decision.kind == 'finish'


def test_specific_media_goal_waits_for_model_to_confirm_selected_target():
    registry = ToolRegistry()
    registry.register('browser_play_media', 'Play observed media', ToolPermission.SAFE, {},
                      lambda _: {'ok': True}, input_model=Arguments)
    state = TaskState(goal='Play the song 777 by Joji', criteria=['777 playing'])
    state.records.append(ActionRecord(
        action=Action(tool='browser_follow_link', arguments={'index': 0}, label='follow'),
        outcome=Outcome(status='accepted', summary='Observed page', data={
            'page_observed': True, 'title': 'Joji - Glimpse of Us',
            'media': [{'paused': True}]}), dispatched=True))
    class Provider:
        async def structured(self, *args):
            return '{"tool":"finish","message":"This is the wrong video."}'
    decision = asyncio.run(OperatorAdapter(registry, state, BudgetedProvider(Provider(), state)).decide(state.context()))
    assert decision.kind != 'act' or decision.action.tool != 'browser_play_media'


def test_empty_clarification_after_action_stops_with_partial_result_instead_of_error():
    registry = ToolRegistry()
    registry.register('observe_marker', 'Observe marker', ToolPermission.SAFE, {},
                      lambda _: {'ok': True, 'marker': 'seen'}, input_model=Arguments)
    class Provider:
        async def structured(self, prompt, system, schema):
            if json.loads(prompt)['untrusted_action_results']:
                return '{"tool":"ask","message":""}'
            return '{"tool":"observe_marker"}'
    state = TaskState(goal='Observe a marker and report what happened', criteria=['marker observed'])
    events = asyncio.run(_collect_run(registry, state, Provider()))
    assert [record.action.tool for record in state.records] == ['observe_marker']
    assert state.model_calls == 3
    assert events[-1][0] == 'final'
    assert events[-1][1]['verified'] is False
    assert 'remaining goal is unverified' in events[-1][1]['text']


def test_interactive_media_goal_does_not_waste_action_on_plain_browser_launch():
    registry = ToolRegistry()
    launched = []
    class AppInput(Arguments):
        application: str
    registry.register('open_application', 'Launch an application', ToolPermission.SAFE, {},
                      lambda p: launched.append(p) or {'ok': True}, input_model=AppInput)
    registry.register('browser_search', 'Search in the agent-owned browser', ToolPermission.SAFE, {},
                      lambda p: {'ok': True}, input_model=BrowserQuery)
    class Provider:
        async def structured(self, prompt, system, schema):
            if json.loads(prompt).get('rejected_browser_launch'):
                return '{"tool":"browser_search","arguments":{"query":"Joji songs","site":"youtube"}}'
            return '{"tool":"open_application","arguments":{"application":"chrome"}}'
    state = TaskState(goal='Open Chrome and play any Joji song on YouTube', criteria=['music playing'])
    decision = asyncio.run(OperatorAdapter(registry, state, BudgetedProvider(Provider(), state)).decide(state.context()))
    assert decision.kind == 'act' and decision.action.tool == 'browser_search'
    assert decision.action.arguments['query'] == 'Joji songs'
    assert state.model_calls == 2 and not launched


async def _collect_run(registry, state, provider):
    return [event async for event in run_operator(registry, state, BudgetedProvider(provider, state), connected)]


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


def test_empty_application_search_can_fall_back_to_running_windows():
    registry = ToolRegistry()
    registry.register('observe_windows', 'See running apps', ToolPermission.SAFE, {},
                      lambda _: {'ok': True}, input_model=Arguments)
    state = TaskState(goal='Use the open unfamiliar app', criteria=['Done'])
    state.records.append(ActionRecord(
        action=Action(tool='application_search', arguments={'query': 'unfamiliar'}, label='Search'),
        outcome=Outcome(status='accepted', summary='No installed match', data={'applications': []}), dispatched=True))
    decision = asyncio.run(OperatorAdapter(registry, state, None).decide(state.context()))
    assert decision.kind == 'act'
    assert decision.action.tool == 'observe_windows'


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


def test_clarification_answer_can_supply_missing_app_name():
    from app.application_tools import SearchApplications
    registry = ToolRegistry()
    registry.register('application_search', 'Search apps', ToolPermission.SAFE, {},
                      lambda p: {'ok': True}, input_model=SearchApplications)
    state = TaskState(goal='Open an app for me.', criteria=['app opened'])
    state.pending_question = 'Which application?'
    state.resume('NoteSpace')
    class Provider:
        async def structured(self, prompt, system, schema):
            return '{"query":"NoteSpace"}' if json.loads(prompt).get('selected_tool') else '{"tool":"application_search"}'
    decision = asyncio.run(OperatorAdapter(registry, state, BudgetedProvider(Provider(), state)).decide(state.context()))
    assert decision.kind == 'act' and decision.action.arguments == {'query': 'NoteSpace'}


def test_incomplete_file_blocks_output_then_replans_to_missing_page():
    from app.file_tools import register
    registry = ToolRegistry()
    register(registry)
    state = TaskState(goal='Read C:/source.txt and create C:/report.md', criteria=['report'])
    state.records.append(ActionRecord(
        action=Action(tool='read_text', arguments={'path': 'C:/source.txt', 'offset': 0}, label='read'),
        outcome=Outcome(status='accepted', summary='Read a page', data={
            'path': 'C:/source.txt', 'text': 'partial', 'offset': 0, 'next_offset': 2048,
            'truncated': True, 'source_version': 'v1'}), dispatched=True))
    class Provider:
        async def structured(self, prompt, system, schema):
            context = json.loads(prompt)
            if context.get('selected_tool') == 'create_text':
                return '{"path":"C:/report.md","text":"Premature report"}'
            if context.get('selected_tool') == 'read_text':
                return '{"path":"C:/source.txt","offset":2048}'
            return '{"tool":"read_text"}' if context.get('incomplete_sources') else '{"tool":"create_text"}'
    decision = asyncio.run(OperatorAdapter(registry, state, BudgetedProvider(Provider(), state)).decide(state.context()))
    assert decision.kind == 'act' and decision.action.tool == 'read_text'
    assert decision.action.arguments['offset'] == 2048


def test_clarification_path_used_for_output_and_plan_is_not_evidence(tmp_path):
    from app.file_tools import register
    registry = ToolRegistry()
    register(registry)
    state = TaskState(goal='Create a new text file containing hello.', criteria=['file correct'])
    state.pending_question = 'Where should I save it?'
    path = str(tmp_path / 'hello.txt')
    state.resume(path)
    class Provider:
        async def structured(self, prompt, system, schema):
            if json.loads(prompt).get('selected_tool'):
                return json.dumps({'path': path, 'text': 'hello'})
            return json.dumps({'tool': 'create_text', 'plan': {
                'outcomes': ['Create file'], 'output_targets': [path], 'remaining_work': ['Write file']}})
    decision = asyncio.run(OperatorAdapter(registry, state, BudgetedProvider(Provider(), state)).decide(state.context()))
    assert decision.kind == 'act' and decision.action.arguments['path'] == path
    assert state.working_plan.output_targets == [path]
    assert state.evidence == []


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
