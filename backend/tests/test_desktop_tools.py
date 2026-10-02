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
