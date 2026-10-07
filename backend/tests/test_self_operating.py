import asyncio
import json

import pytest

from app.approvals import ApprovalStore
from app.self_operating import parse_operations, run_self_operating


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


def test_reference_keyboard_batch_then_fresh_screen_before_done():
    desktop = Desktop(None)
    images = []
    class Provider:
        async def structured_images(self, prompt, system, schema, frames):
            images.extend(frames)
            if len(images) == 1:
                return json.dumps([{'operation': 'press', 'keys': ['win', 's']},
                    {'operation': 'write', 'content': 'Calculator'},
                    {'operation': 'press', 'keys': ['enter']}])
            assert len(json.loads(prompt)['recent_actions']) == 3
            return '{"operations":[{"operation":"done","summary":"Calculator visible."}]}'
    async def run():
        return [event async for event in run_self_operating('Open Calculator', Provider(), connected,
            ApprovalStore(), desktop_factory=lambda stop: desktop)]
    events = asyncio.run(run())
    assert desktop.calls == [('press', ['win', 's']), ('write', 'Calculator'), ('press', ['enter'])]
    assert images == [b'frame-1', b'frame-2']
    assert events[-1][0] == 'final'
    assert events[-1][1]['verified'] is False


@pytest.mark.parametrize('raw', [
    '[{"operation":"click","x":500,"y":0.2}]',
    '[{"operation":"write","content":"x"},{"operation":"done","summary":"Done"}]',
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
