import base64

import pytest

from app.screen_tools import ScreenSession, register
from app.tools import ToolPermission, ToolRegistry


class Desktop:
    def window_identity(self, window_id, observation_id, max_age=10):
        if (window_id, observation_id) != (12, 7):
            raise ValueError('Stale screen target.')
        return {'hwnd': 12, 'pid': 40, 'title': 'Fixture', 'process': 'fixture.exe',
                'executable': 'C:/fixture.exe', 'password_controls_present': False}


class Response:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


class Client:
    def __init__(self, calls):
        self.calls = calls

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def get(self, url):
        self.calls.append(('get', url))
        return Response({'models': [{'name': 'vision-fixture', 'capabilities': ['vision']} ]})

    def post(self, url, json):
        self.calls.append(('post', url, json))
        if url.endswith('/api/show'):
            return Response({'capabilities': ['vision']})
        return Response({'response': 'A blue button is visible.'})


def session(calls, *, foreground=lambda: 12, base_url='http://127.0.0.1:11434'):
    return ScreenSession(Desktop(), base_url=base_url, model='vision-fixture',
                         capture=lambda rect: b'\x89PNG\r\n\x1a\nfixture',
                         rect=lambda window_id: [0, 0, 20, 20], foreground=foreground,
                         clock=lambda: 100.0, client_factory=lambda **kwargs: Client(calls))


def test_screen_capture_is_approved_bound_to_fresh_window_and_local_only():
    calls = []
    registry = ToolRegistry()
    register(registry, Desktop(), session(calls))
    tool = registry.get_tool('screen_inspect')
    assert tool.permission == ToolPermission.CONFIRMATION_REQUIRED
    args = {'window_id': 12, 'observation_id': 7, 'purpose': 'Identify controls'}
    canonical = registry.prepare('screen_inspect', args)
    assert canonical['window_title'] == 'Fixture'
    assert canonical['process'] == 'fixture.exe'
    with pytest.raises(PermissionError):
        registry.execute('screen_inspect', args)
    approval = registry.approvals.request('task', tool.name, tool.revision, canonical)
    registry.approvals.respond(approval.id, approval.token, True)
    result = registry.execute('screen_inspect', args, approval_id=approval.id, task_id='task')
    assert result['description'] == 'A blue button is visible.'
    assert 'images' not in result
    assert calls[1][1] == 'http://127.0.0.1:11434/api/generate'
    assert base64.b64decode(calls[1][2]['images'][0]).startswith(b'\x89PNG')


def test_screen_capture_rejects_background_stale_and_remote_targets():
    calls = []
    background = session(calls, foreground=lambda: 99)
    with pytest.raises(ValueError, match='not foreground'):
        background.prepare({'window_id': 12, 'observation_id': 7, 'purpose': 'Identify controls'})
    with pytest.raises(ValueError, match='Stale'):
        session(calls).prepare({'window_id': 12, 'observation_id': 6, 'purpose': 'Identify controls'})
    with pytest.raises(ValueError, match='only to a local'):
        session(calls, base_url='https://example.com').prepare(
            {'window_id': 12, 'observation_id': 7, 'purpose': 'Identify controls'})
    assert not calls


def test_foreground_change_after_capture_never_sends_pixels():
    calls = []
    foreground = [12]
    tool = session(calls, foreground=lambda: foreground[0])
    def change_foreground(rect):
        foreground[0] = 99
        return b'\x89PNG\r\n\x1a\nfixture'
    tool.capture = change_foreground
    with pytest.raises(ValueError, match='not foreground'):
        tool.inspect(window_id=12, observation_id=7, purpose='Identify controls')
    assert not any(call[1].endswith('/api/generate') for call in calls)


def test_known_password_control_blocks_capture():
    calls = []
    class PasswordDesktop(Desktop):
        def window_identity(self, *args, **kwargs):
            return {**super().window_identity(*args, **kwargs), 'password_controls_present': True}
    tool = ScreenSession(PasswordDesktop(), base_url='http://127.0.0.1:11434',
                         model='vision-fixture', foreground=lambda: 12,
                         capture=lambda rect: pytest.fail('Pixels must not be captured.'),
                         client_factory=lambda **kwargs: Client(calls))
    with pytest.raises(ValueError, match='password control'):
        tool.prepare({'window_id': 12, 'observation_id': 7, 'purpose': 'Identify controls'})
    assert not calls
