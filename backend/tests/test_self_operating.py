import asyncio
import json

import pytest

from app.approvals import ApprovalStore
from app.self_operating import Operation, operation_schema, parse_operations, run_self_operating


class Desktop:
    def __init__(self, stopped):
        self.calls = []
        self.frames = 0
    def screenshot(self):
        self.frames += 1
        return f'frame-{self.frames}'.encode()
    def press(self, keys): self.calls.append(('press', keys))
    def write(self, content): self.calls.append(('write', content))
    def mouse(self, detail): self.calls.append(('click', detail))
    def wait(self, seconds): pass


async def connected(): return False


def review_response(complete=True):
    return json.dumps({'goal_complete': complete, 'checks': [
        {'criterion': 1, 'satisfied': complete, 'evidence': 'Requested result is visible' if complete else 'Only the app is open'}],
        'remaining': [] if complete else ['Perform the requested calculation']})


def test_search_is_observed_before_typing_then_app_observed_before_done():
    desktop = Desktop(None)
    images = []
    class Provider:
        async def structured_images(self, prompt, system, schema, frames):
            images.extend(frames)
            if 'goal_complete' in schema['properties']:
                return review_response()
            if len(images) == 1:
                return json.dumps([{'operation': 'press', 'keys': ['win', 's']},
                    {'operation': 'write', 'content': 'Calculator'},
                    {'operation': 'press', 'keys': ['enter']}])
            if len(images) == 2:
                assert desktop.calls == [('press', ['win', 's'])]
                assert 'Remaining batch actions were NOT sent' in prompt
                return json.dumps([{'operation': 'write', 'content': 'Calculator'},
                    {'operation': 'press', 'keys': ['enter']}])
            assert desktop.calls == [('press', ['win', 's']), ('write', 'Calculator'), ('press', ['enter'])]
            return '{"operations":[{"operation":"done","summary":"Calculator visible."}]}'
    async def run():
        return [event async for event in run_self_operating('Open Calculator', Provider(), connected,
            ApprovalStore(), desktop_factory=lambda stop: desktop)]
    events = asyncio.run(run())
    assert desktop.calls == [('press', ['win', 's']), ('write', 'Calculator'), ('press', ['enter'])]
    assert images == [b'frame-1', b'frame-2', b'frame-3', b'frame-4']
    assert events[-1][0] == 'final'
    assert events[-1][1]['verified'] is False


@pytest.mark.parametrize('raw', [
    '[{"operation":"click","x":500,"y":0.2}]',
    '[{"operation":"done","summary":"Done"},{"operation":"write","content":"x"}]',
    '[{"operation":"press","keys":[]}]', '[{"operation":"write"}]'])
def test_invalid_batch_never_dispatched(raw):
    with pytest.raises(ValueError): parse_operations(raw)


def test_failure_observes_before_remaining_actions():
    desktop = Desktop(None)
    def fail(content): raise RuntimeError('Input failed after possible partial effect')
    desktop.write = fail
    class Provider:
        async def structured_images(self, *args):
            if desktop.frames == 1:
                return '[{"operation":"write","content":"Hello"},{"operation":"press","keys":["enter"]}]'
            return '[{"operation":"ask","summary":"Please check the text."}]'
    async def run():
        return [e async for e in run_self_operating('Type Hello', Provider(), connected,
            ApprovalStore(), desktop_factory=lambda stop: desktop)]
    events = asyncio.run(run())
    assert desktop.frames == 2
    assert desktop.calls == []
    assert events[-1][0] == 'clarification'


def test_disconnect_stops_before_any_input():
    async def disconnected(): return True
    desktop = Desktop(None)
    async def run():
        with pytest.raises(asyncio.CancelledError):
            async for _ in run_self_operating('Open app', None, disconnected,
                    ApprovalStore(), desktop_factory=lambda stop: desktop): pass
        await asyncio.sleep(0.05)
    asyncio.run(run())
    assert desktop.calls == []


def test_repeated_batch_is_replanned_without_duplicate_typing():
    desktop = Desktop(None)
    class Provider:
        calls = 0
        async def structured_images(self, prompt, *args):
            if 'original_goal' in json.loads(prompt):
                return review_response()
            self.calls += 1
            if self.calls <= 2:
                return '[{"operation":"write","content":"Hello"}]'
            assert 'already sent' in prompt
            return '[{"operation":"done","summary":"Hello is visible."}]'
    async def run():
        return [e async for e in run_self_operating('Type Hello', Provider(), connected,
            ApprovalStore(), desktop_factory=lambda stop: desktop)]
    events = asyncio.run(run())
    assert desktop.calls == [('write', 'Hello')]
    assert events[-1][1]['outcome'] == 'completed'


def test_premature_completion_returns_to_work_before_reporting_success():
    desktop = Desktop(None)
    class Provider:
        decisions = 0
        async def structured_images(self, prompt, system, schema, frames):
            if 'goal_complete' in schema['properties']:
                return review_response(bool(desktop.calls))
            self.decisions += 1
            if self.decisions == 2:
                assert 'Perform the requested calculation' in prompt
                return '[{"operation":"write","content":"72*2"},{"operation":"press","keys":["enter"]}]'
            return '[{"operation":"done","summary":"Finished"}]'
    async def run():
        return [e async for e in run_self_operating('Calculate 72 * 2', Provider(), connected,
            ApprovalStore(), desktop_factory=lambda stop: desktop)]
    events = asyncio.run(run())
    assert desktop.calls == [('write', '72*2'), ('press', ['enter'])]
    assert len([e for e in events if e[0] == 'final']) == 1
    assert events[-1][1]['verification'] == 'separate_visual_review'


def test_repeated_false_completion_never_reports_completed():
    class Provider:
        async def structured_images(self, prompt, system, schema, frames):
            return review_response(False) if 'goal_complete' in schema['properties'] else '[{"operation":"done","summary":"App opened"}]'
    async def run():
        return [e async for e in run_self_operating('Open app and do work', Provider(), connected,
            ApprovalStore(), desktop_factory=Desktop)]
    events = asyncio.run(run())
    assert events[-1][1]['outcome'] == 'unverified'


def test_window_change_after_click_reobserves_before_typing():
    desktop = Desktop(None)
    desktop.context = lambda: {'active_window': 'Chrome profile picker' if desktop.calls else 'Desktop'}
    class Provider:
        async def structured_images(self, prompt, *args):
            if desktop.frames == 1:
                return '[{"operation":"click","x":0.5,"y":0.9},{"operation":"write","content":"must not type into a new window"}]'
            assert 'Chrome profile picker' in prompt
            return '[{"operation":"ask","summary":"Which profile should I use?"}]'
    async def run():
        return [e async for e in run_self_operating('Open browser', Provider(), connected,
            ApprovalStore(), desktop_factory=lambda stop: desktop)]
    events = asyncio.run(run())
    assert desktop.calls == [('click', {'x': 0.5, 'y': 0.9})]
    assert desktop.frames == 2
    assert events[-1][0] == 'clarification'


def test_long_batch_executes_only_bounded_prefix():
    actions = [{'operation': 'press', 'keys': ['tab']}] * 8
    assert len(parse_operations(json.dumps(actions))) == 6


def test_provider_schema_advertises_all_supported_actions():
    variants = operation_schema()['properties']['operations']['items']['anyOf']
    assert {item['properties']['operation']['const'] for item in variants} == set(
        Operation.model_json_schema()['properties']['operation']['enum'])


def test_decision_prompt_and_schema_are_prepared_once_per_task(monkeypatch):
    from app import self_operating as engine
    calls = []
    original_prompt, original_schema = engine.system_prompt, engine.operation_schema
    def prompt(goal):
        calls.append('prompt')
        return original_prompt(goal)
    def schema():
        calls.append('schema')
        return original_schema()
    monkeypatch.setattr(engine, 'system_prompt', prompt)
    monkeypatch.setattr(engine, 'operation_schema', schema)
    desktop = Desktop(None)
    class Provider:
        async def structured_images(self, *args):
            if desktop.frames == 1:
                return '[{"operation":"write","content":"hello"}]'
            return '[{"operation":"ask","summary":"Test ends."}]'
    async def run():
        return [e async for e in engine.run_self_operating('Type hello', Provider(), connected,
            ApprovalStore(), desktop_factory=lambda stop: desktop)]
    asyncio.run(run())
    assert desktop.frames == 2
    assert calls == ['prompt', 'schema']


def test_invented_app_shortcut_replans_before_any_input():
    desktop = Desktop(None)
    class Provider:
        calls = 0
        async def structured_images(self, prompt, *args):
            self.calls += 1
            if self.calls == 1:
                return '[{"operation":"press","keys":["win","n"],"thought":"Open the editor"},{"operation":"write","content":"648"}]'
            if self.calls == 2:
                assert desktop.calls == []
                assert 'notifications' in prompt
                return '[{"operation":"press","keys":["win","s"]}]'
            return '[{"operation":"ask","summary":"Test ends after Search."}]'
    async def run():
        return [e async for e in run_self_operating('Transfer the calculation result to an editor',
            Provider(), connected, ApprovalStore(), desktop_factory=lambda stop: desktop)]
    events = asyncio.run(run())
    assert desktop.calls == [('press', ['win', 's'])]
    assert any(event == 'status' and payload['stage'] == 'recovering' for event, payload in events)


@pytest.mark.parametrize('keys', [['alt', 'tab'], ['enter'], ['ctrl', 't']])
def test_navigation_discards_queued_typing_until_new_observation(keys):
    desktop = Desktop(None)
    class Provider:
        async def structured_images(self, *args):
            if desktop.frames == 1:
                return json.dumps([{'operation': 'press', 'keys': keys},
                                   {'operation': 'write', 'content': 'wrong context'}])
            return '[{"operation":"ask","summary":"Test ends at new observation."}]'
    async def run():
        return [e async for e in run_self_operating('Switch context', Provider(), connected,
            ApprovalStore(), desktop_factory=lambda stop: desktop)]
    asyncio.run(run())
    assert desktop.calls == [('press', keys)]
    assert desktop.frames == 2
