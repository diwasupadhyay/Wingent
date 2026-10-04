import asyncio
import json
from types import SimpleNamespace

import pytest

from app.brain import AgentBrain
from app.computer_tools import ComputerSession, ComputerAction, register
from app.tools import ToolRegistry, ToolPermission, execution_task_id


class Desktop:
    def __init__(self):
        self.foreground = 1
        self.bounds = [0, 0, 800, 600]
        self.signature = [0] * 768
        self.calls = []

    def list_visible_windows(self):
        return [dict(hwnd=1, pid=10, executable='test.exe', process='test.exe', title='Test')]

    def foreground_window_id(self):
        return self.foreground

    def focus(self, window_id):
        self.foreground = window_id

    def rectangle(self, window_id):
        return self.bounds[:]

    def capture(self, rect):
        return dict(image=b'pixels', signature=self.signature[:], width=800, height=600)

    def accessibility(self, window_id):
        return dict(controls=[dict(id='button', name='Submit'), dict(id='edit', name='Text', role='ControlType.Edit', focused=True)])

    def dispatch(self, window_id, rect, action, cancelled):
        assert not cancelled()
        self.calls.append(action)


@pytest.fixture
def granted():
    desktop = Desktop()
    session = ComputerSession(desktop)
    token = execution_task_id.set('owner')
    frame = session.begin(window_id=1, purpose='Test isolated window')
    yield session, desktop, frame
    execution_task_id.reset(token)


def test_action_looks_again_and_cannot_replay_frame(granted):
    session, desktop, frame = granted
    action = dict(frame_id=frame['frame_id'], kind='type', text='Hello')
    result = session.act(**action)
    assert result['post_observation']['frame_id'] != frame['frame_id']
    assert result['goal_verified'] is False
    assert session.act(**action)['effect'] == 'no_effect'
    assert len(desktop.calls) == 1


@pytest.mark.parametrize('change', ['focus', 'bounds', 'pixels', 'time'])
def test_changed_observation_does_not_dispatch(granted, change):
    session, desktop, frame = granted
    if change == 'focus': desktop.foreground = 2
    if change == 'bounds': desktop.bounds[0] = 50
    if change == 'pixels': desktop.signature = [9] * 768
    if change == 'time': session.tasks['owner']['frame']['at'] -= 121
    result = session.act(frame_id=frame['frame_id'], kind='click', x=500, y=500)
    assert result['effect'] == 'no_effect'
    assert not desktop.calls


@pytest.mark.parametrize('change', ['focus', 'bounds'])
def test_visual_context_drops_observation_after_window_changes(granted, change):
    session, desktop, _ = granted
    if change == 'focus':
        desktop.foreground = 2
    else:
        desktop.bounds[0] = 50
    assert session.visual_context('owner') is None
    assert session.tasks['owner']['frame'] is None
    assert session.tasks['owner']['input_targeted'] is False


def test_focused_non_input_control_clears_typing_target(granted):
    session, desktop, frame = granted
    desktop.accessibility = lambda _: {'controls': [
        {'id': 'button', 'name': 'OK', 'role': 'ControlType.Button', 'focused': True}]}
    session.observe(1)
    assert session.visual_context('owner')['input_targeted'] is False
    result = session.act(frame_id=session.tasks['owner']['frame']['id'], kind='type', text='Hello')
    assert result['effect'] == 'no_effect'
    assert not desktop.calls


def test_grant_is_task_scoped_and_revocable(granted):
    session, desktop, frame = granted
    token = execution_task_id.set('other')
    with pytest.raises(ValueError): session.observe(1)
    execution_task_id.reset(token)
    session.cancel('owner')
    with pytest.raises(ValueError): session.observe(1)
    session.close_task('owner')
    assert session.visual_context('owner') is None


def test_begin_accepts_process_name_from_window_observation():
    desktop = Desktop()
    session = ComputerSession(desktop)
    token = execution_task_id.set('owner')
    try:
        result = session.begin(window_id=1, purpose='Type in this window',
                               window_title='Test', process='test.exe')
        assert result['ok'] is True
        with pytest.raises(ValueError, match='identity changed'):
            session.prepare_begin({'window_id': 1, 'purpose': 'Type in this window',
                                   'process': 'other.exe'})
    finally:
        execution_task_id.reset(token)


def test_unobserved_accessibility_target_is_rejected(granted):
    session, desktop, frame = granted
    assert session.act(frame_id=frame['frame_id'], kind='invoke', target_id='invented')['effect'] == 'no_effect'
    assert not desktop.calls


def test_brain_attaches_pixels_without_putting_them_in_history(granted):
    session, _, _ = granted
    calls = []
    class Provider:
        async def structured_images(self, prompt, system, schema, images):
            calls.append((json.loads(prompt), system, images))
            return '{"tool":"finish"}'
    brain = AgentBrain(Provider(), SimpleNamespace(computer_session=session), SimpleNamespace(id='owner'))
    asyncio.run(brain.structured('{"goal":"test"}', 'system', {}))
    assert calls[0][2] == [b'pixels']
    assert 'image' not in calls[0][0]['current_computer_frame']
    assert 'untrusted' in calls[0][1]


def test_control_requires_explicit_grant_and_sensitive_action_approval():
    registry = ToolRegistry()
    register(registry, ComputerSession(Desktop()))
    assert registry.get_tool('computer_begin').permission == ToolPermission.CONFIRMATION_REQUIRED
    assert registry.get_tool('computer_confirm_action').permission == ToolPermission.CONFIRMATION_REQUIRED
    with pytest.raises(ValueError): ComputerAction(frame_id='frame', kind='click')


def test_pixels_cannot_be_sent_to_remote_ollama():
    from app.llm import OllamaClient
    with pytest.raises(ValueError, match='local Ollama'):
        asyncio.run(OllamaClient('https://example.com').structured_images('{}', '', {}, [b'pixels']))


def test_submission_needs_exact_approval_even_with_window_grant(granted):
    session, desktop, frame = granted
    args = dict(frame_id=frame['frame_id'], kind='hotkey', keys=['enter'])
    assert session.act(**args)['effect'] == 'no_effect'
    assert not desktop.calls
    assert session.act(_confirmed=True, **args)['ok']


def test_concurrent_task_cannot_take_over_desktop(granted):
    session, _, _ = granted
    token = execution_task_id.set('other')
    try:
        with pytest.raises(ValueError, match='Another task'):
            session.begin(window_id=1, purpose='Competing task')
    finally:
        execution_task_id.reset(token)


def test_focus_denial_is_actionable_no_effect_and_discards_frame(granted):
    session, desktop, frame = granted
    registry = ToolRegistry()
    register(registry, session)
    def denied(_):
        raise ValueError('Windows did not grant focus to the selected window.')
    desktop.focus = denied
    token = execution_task_id.set('owner')
    try:
        result = registry.get_tool('computer_observe').executor({'window_id': 1})
    finally:
        execution_task_id.reset(token)
    assert result['effect'] == 'no_effect'
    assert result['needs_user_attention'] is True
    assert session.visual_context('owner') is None
