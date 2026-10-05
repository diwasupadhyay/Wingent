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


def test_cannot_begin_control_of_agent_overlay():
    desktop = Desktop()
    desktop.list_visible_windows = lambda: [dict(hwnd=1, pid=10, executable='app.exe', process='app.exe', title='Wingent')]
    with pytest.raises(ValueError, match='own overlay'):
        ComputerSession(desktop).prepare_begin({'window_id': 1})


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


class MultiWindowDesktop(Desktop):
    def __init__(self):
        super().__init__()
        self.windows = super().list_visible_windows() + [
            dict(hwnd=2, pid=20, executable='other.exe', process='other.exe', title='Other')]

    def list_visible_windows(self):
        return self.windows


def test_desktop_scope_switches_observed_apps_and_follows_new_dialog():
    desktop = MultiWindowDesktop()
    session = ComputerSession(desktop)
    token = execution_task_id.set('desktop-test')
    try:
        first = session.begin(window_id=1, scope='desktop', purpose='Work across apps')
        assert len(first['windows']) == 2
        switched = session.observe(2)
        assert switched['window_id'] == 2
        assert session.act(frame_id=first['frame_id'], kind='type', text='stale')['effect'] == 'no_effect'
        def open_dialog(*_):
            desktop.windows.append(dict(hwnd=3, pid=20, executable='other.exe', process='other.exe', title='Dialog'))
            desktop.foreground = 3
        desktop.dispatch = open_dialog
        result = session.act(frame_id=switched['frame_id'], kind='click', x=500, y=500)
        assert result['action_window_id'] == 2
        assert result['post_observation']['window_id'] == 3
        assert session.visual_context('desktop-test')['window_id'] == 3
        assert desktop.foreground == 3
    finally:
        session.close_task('desktop-test')
        execution_task_id.reset(token)


def test_desktop_scope_rejects_reused_or_unobserved_switch_targets():
    desktop = MultiWindowDesktop()
    session = ComputerSession(desktop)
    token = execution_task_id.set('desktop-test')
    try:
        session.begin(window_id=1, scope='desktop', purpose='Work across apps')
        desktop.windows[1] = {**desktop.windows[1], 'pid': 999}
        with pytest.raises(ValueError, match='identity changed'):
            session.observe(2)
        with pytest.raises(ValueError):
            session.observe(999)
        assert desktop.foreground == 1
    finally:
        session.close_task('desktop-test')
        execution_task_id.reset(token)


def test_window_scope_does_not_silently_expand_to_foreground_dialog(granted):
    session, desktop, _ = granted
    desktop.foreground = 2
    with pytest.raises(ValueError, match='not been granted'):
        session.observe()


def test_non_actionable_uia_control_reports_known_no_effect(granted):
    session, desktop, frame = granted
    session.tasks['owner']['frame']['controls'][0]['actions'] = []
    result = session.act(frame_id=frame['frame_id'], kind='invoke', target_id='button')
    assert result['effect'] == 'no_effect'
    assert 'screenshot' in result['reason']
    assert not desktop.calls


def test_opaque_focused_container_preserves_visual_click_target():
    desktop = Desktop()
    desktop.accessibility = lambda _: {'controls': [{'id': 'canvas', 'role': 'ControlType.Pane', 'focused': True}]}
    session = ComputerSession(desktop)
    token = execution_task_id.set('canvas-test')
    try:
        frame = session.begin(window_id=1, purpose='Use unfamiliar canvas app')
        assert session.visual_context('canvas-test')['input_targeted'] is False
        clicked = session.act(frame_id=frame['frame_id'], kind='click', x=500, y=300)
        assert session.visual_context('canvas-test')['input_targeted'] is True
        typed = session.act(frame_id=clicked['post_observation']['frame_id'], kind='type', text='Hello')
        assert typed['ok']
    finally:
        session.close_task('canvas-test')
        execution_task_id.reset(token)


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


def test_noncomputer_argument_repair_skips_repeated_vision_call(granted):
    session, _, _ = granted
    calls = []
    class Provider:
        async def structured(self, prompt, system, schema):
            calls.append('text')
            return '{}'
        async def structured_images(self, prompt, system, schema, images):
            calls.append('image')
            return '{}'
    brain = AgentBrain(Provider(), SimpleNamespace(computer_session=session), SimpleNamespace(id='owner'))
    asyncio.run(brain.structured('{"selected_tool":"read_text"}', 'repair', {}))
    asyncio.run(brain.structured('{"selected_tool":"computer_action"}', 'repair', {}))
    assert calls == ['text', 'image']


def test_control_requires_explicit_grant_and_sensitive_action_approval():
    registry = ToolRegistry()
    register(registry, ComputerSession(Desktop()))
    assert registry.get_tool('computer_begin').permission == ToolPermission.SAFE
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


def test_drag_always_requires_exact_approval(granted):
    session, desktop, frame = granted
    args = ComputerAction(frame_id=frame['frame_id'], kind='drag', x=100, y=200,
                          end_x=600, end_y=200).model_dump(exclude_none=True)
    assert session.act(**args)['effect'] == 'no_effect'
    assert not desktop.calls
    assert session.act(_confirmed=True, **args)['ok']


@pytest.mark.parametrize('arguments', [
    {'kind': 'hover'}, {'kind': 'drag', 'x': 1, 'y': 2},
    {'kind': 'wait', 'duration_ms': 10000},
    {'kind': 'drag', 'x': 0, 'y': 0, 'end_x': 1001, 'end_y': 2},
])
def test_pointer_and_wait_arguments_are_bounded(arguments):
    with pytest.raises(ValueError):
        ComputerAction(frame_id='fresh', **arguments)


def test_interrupted_drag_releases_mouse_button(monkeypatch):
    from app import windows_computer as native
    fake = SimpleNamespace(GetAsyncKeyState=lambda _: 0, SetCursorPos=lambda *_: True,
                           WindowFromPoint=lambda _: 1, GetAncestor=lambda *_: 1)
    monkeypatch.setattr(native, 'user32', lambda: fake)
    monkeypatch.setattr(native, 'foreground_window_id', lambda: 1)
    events = []
    monkeypatch.setattr(native, 'send', lambda items: events.extend(item.mouse.dwFlags for item in items))
    checks = []
    def cancelled():
        checks.append(True)
        return len(checks) > 3
    with pytest.raises(RuntimeError, match='stopped'):
        native._dispatch(1, [0, 0, 800, 600], dict(kind='drag', x=100, y=100,
                         end_x=600, end_y=100, duration_ms=100), cancelled)
    assert events == [2, 4]  # Down then release, even after partial movement.


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
