from app.desktop_tools import DesktopSession, register
from app.tools import ToolPermission, ToolRegistry


def test_observed_control_can_be_clicked_once_and_typing_requires_new_observation():
    now = [100.0]
    window = {'hwnd': 12, 'pid': 40, 'executable': 'C:/fixture.exe',
              'title': 'Fixture', 'process': 'fixture.exe'}
    control = {'control_id': 14, 'class': 'Edit', 'text': '',
               'rect': [0, 0, 100, 40], 'password': False}
    clicks, typed = [], []
    session = DesktopSession(snapshot=lambda _: [control.copy()], windows=lambda: [window.copy()],
                             clock=lambda: now[0], click=lambda *args: clicks.append(args),
                             type_text=lambda *args: typed.append(args))
    observation = session.observe(12)
    assert session.click(12, 14, observation['observation_id'])['effect'] == 'accepted'
    assert len(clicks) == 1
    assert session.type_text(12, 14, observation['observation_id'], 'hello')['effect'] == 'no_effect'
    newer = session.observe(12)
    assert session.type_text(12, 14, newer['observation_id'], 'hello')['effect'] == 'accepted'
    assert typed == [(12, 14, 'hello')]


def test_stale_or_changed_control_never_dispatches():
    now = [100.0]
    state = {'title': 'Fixture', 'text': 'Send'}
    calls = []
    session = DesktopSession(
        snapshot=lambda _: [{'control_id': 14, 'class': 'Button', 'text': state['text'],
                              'rect': [0, 0, 100, 40], 'password': False}],
        windows=lambda: [{'hwnd': 12, 'pid': 40, 'executable': 'fixture.exe',
                          'title': state['title'], 'process': 'fixture.exe'}],
        clock=lambda: now[0], click=lambda *args: calls.append(args))
    first = session.observe(12)
    state['text'] = 'Delete'
    assert session.click(12, 14, first['observation_id'])['effect'] == 'no_effect'
    second = session.observe(12)
    now[0] += 11
    assert session.click(12, 14, second['observation_id'])['effect'] == 'no_effect'
    assert not calls


def test_input_tools_require_exact_action_approval():
    registry = ToolRegistry()
    session = DesktopSession(snapshot=lambda _: [], windows=lambda: [])
    register(registry, session)
    assert registry.get_tool('desktop_observe').permission == ToolPermission.SAFE
    assert registry.get_tool('desktop_click_control').permission == ToolPermission.CONFIRMATION_REQUIRED
    assert registry.get_tool('desktop_type_text').permission == ToolPermission.CONFIRMATION_REQUIRED


def test_click_returns_fresh_bounded_post_action_observation(monkeypatch):
    monkeypatch.setattr('app.desktop_tools.time.sleep', lambda _: None)
    state = {'text': 'Before'}
    window = {'hwnd': 12, 'pid': 40, 'executable': 'fixture.exe',
              'title': 'Fixture', 'process': 'fixture.exe'}
    session = DesktopSession(
        snapshot=lambda _: [{'control_id': 14, 'class': 'Button', 'text': state['text'],
                              'rect': [0, 0, 100, 40], 'password': False}],
        windows=lambda: [window.copy()],
        click=lambda *args: state.update(text='After'))
    observed = session.observe(12)
    result = session.click(12, 14, observed['observation_id'])
    assert result['effect'] == 'accepted'
    assert result['post_observation']['controls'][0]['text'] == 'After'
    assert result['post_observation']['observation_id'] > observed['observation_id']


def test_key_requires_fresh_window_and_returns_post_observation(monkeypatch):
    monkeypatch.setattr('app.desktop_tools.time.sleep', lambda _: None)
    now = [100.0]
    state = {'title': 'Fixture', 'text': 'Before'}
    calls = []
    session = DesktopSession(
        snapshot=lambda _: [{'control_id': 14, 'class': 'Button', 'text': state['text'],
                              'rect': [0, 0, 100, 40], 'password': False}],
        windows=lambda: [{'hwnd': 12, 'pid': 40, 'executable': 'fixture.exe',
                          'title': state['title'], 'process': 'fixture.exe'}],
        clock=lambda: now[0],
        press_key=lambda window_id, key: (calls.append((window_id, key)), state.update(text='After')),
        foreground=lambda: 12)
    observation = session.observe(12)
    state['title'] = 'Different'
    assert session.press_key(12, observation['observation_id'], 'enter')['effect'] == 'no_effect'
    assert not calls
    state['title'] = 'Fixture'
    now[0] += 11
    assert session.press_key(12, observation['observation_id'], 'enter')['effect'] == 'no_effect'
    fresh = session.observe(12)
    result = session.press_key(12, fresh['observation_id'], 'enter')
    assert calls == [(12, 'enter')]
    assert result['effect'] == 'accepted'
    assert result['post_observation']['controls'][0]['text'] == 'After'
    assert result['post_observation']['is_foreground'] is True
    assert session.press_key(12, fresh['observation_id'], 'enter')['effect'] == 'no_effect'


def test_key_tool_has_exact_action_approval_and_bounded_schema():
    registry = ToolRegistry()
    register(registry, DesktopSession(snapshot=lambda _: [], windows=lambda: []))
    tool = registry.get_tool('desktop_press_key')
    assert tool.permission == ToolPermission.CONFIRMATION_REQUIRED
    assert 'enter' in str(tool.input_model.model_json_schema())
    assert 'ctrl_alt_delete' not in str(tool.input_model.model_json_schema())
