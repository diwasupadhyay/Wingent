import pytest

from app.browser_tools import BrowserSession, _public_url, register
from app.tools import ToolRegistry


def test_browser_tools_use_isolated_session_and_typed_contracts():
    class Session:
        def __init__(self):
            self.calls = []
        def search(self, **kwargs):
            self.calls.append(('search', kwargs))
            return {'ok': True, 'url': 'https://www.youtube.com/results?search_query=joji'}
        def navigate(self, url):
            self.calls.append(('open', url))
            return {'ok': True, 'url': url}
        def inspect(self):
            return {'ok': True, 'links': []}
        def follow(self, index):
            self.calls.append(('follow', index))
            return {'ok': True}
        def play_media(self):
            return {'ok': False, 'effect': 'no_effect', 'reason': 'No media'}
    session = Session()
    registry = ToolRegistry()
    register(registry, session)
    assert registry.execute('browser_search', {'query': 'joji', 'site': 'youtube'})['ok']
    assert registry.execute('browser_open', {'url': 'https://www.youtube.com'})['ok']
    assert registry.execute('browser_follow_link', {'index': 2})['ok']
    assert registry.execute('browser_play_media', {})['effect'] == 'no_effect'
    assert session.calls == [('search', {'query': 'joji', 'site': 'youtube'}),
                             ('open', 'https://www.youtube.com'), ('follow', 2)]


def test_browser_observation_only_exposes_bounded_http_links(monkeypatch):
    session = BrowserSession()
    monkeypatch.setattr(session, '_start', lambda: None)
    monkeypatch.setattr(session, '_evaluate', lambda expression: {
        'url': 'https://www.youtube.com/results', 'title': 'Results',
        'links': [{'text': 'Joji song', 'url': 'https://www.youtube.com/watch?v=one'},
                  {'text': 'duplicate', 'url': 'https://www.youtube.com/watch?v=one'},
                  {'text': 'unsafe', 'url': 'javascript:alert(1)'}],
        'media': [],
    })
    observation = session.inspect()
    assert observation['links'] == [{'index': 0, 'text': 'Joji song',
                                     'url': 'https://www.youtube.com/watch?v=one'}]
    with pytest.raises(ValueError):
        _public_url('file:///secret')


def test_follow_rejects_unobserved_index(monkeypatch):
    session = BrowserSession()
    monkeypatch.setattr(session, '_start', lambda: None)
    result = session.follow(0)
    assert result['effect'] == 'no_effect'
    assert 'latest live browser observation' in result['reason']


def test_control_crash_falls_back_to_visible_chrome_without_claiming_page(monkeypatch):
    session = BrowserSession()
    monkeypatch.setattr(session, '_start', lambda: (_ for _ in ()).throw(RuntimeError('CDP crashed')))
    monkeypatch.setattr(session, 'close', lambda: None)
    monkeypatch.setattr('app.browser_tools.resolve_browser', lambda browser: 'C:/Chrome/chrome.exe')
    launched = []
    monkeypatch.setattr('app.browser_tools.subprocess.Popen',
                        lambda argv, **kwargs: launched.append(argv))
    windows = iter([[], [{'hwnd': 22, 'executable': 'C:/Chrome/chrome.exe'}]])
    monkeypatch.setattr('app.browser_tools.list_visible_windows', lambda: next(windows))
    result = session.search('joji music video')
    assert launched == [['C:/Chrome/chrome.exe', '--new-window',
                         'https://www.youtube.com/results?search_query=joji+music+video']]
    assert result['new_window_visible'] is True
    assert result['page_observed'] is False
    assert result['browser_control'] is False
    assert session.play_media()['effect'] == 'no_effect'


def test_control_and_visible_launch_failure_is_unknown(monkeypatch):
    session = BrowserSession()
    monkeypatch.setattr(session, '_start', lambda: (_ for _ in ()).throw(RuntimeError('CDP crashed')))
    monkeypatch.setattr(session, 'close', lambda: None)
    monkeypatch.setattr('app.browser_tools.resolve_browser', lambda browser: 'C:/Chrome/chrome.exe')
    monkeypatch.setattr('app.browser_tools.subprocess.Popen', lambda argv, **kwargs: None)
    monkeypatch.setattr('app.browser_tools.list_visible_windows', lambda: [])
    monkeypatch.setattr('app.browser_tools.time.sleep', lambda seconds: None)
    assert session.search('joji')['effect'] == 'unknown'


def test_existing_chrome_window_does_not_verify_new_launch(monkeypatch):
    session = BrowserSession()
    monkeypatch.setattr(session, '_start', lambda: (_ for _ in ()).throw(RuntimeError('CDP crashed')))
    monkeypatch.setattr(session, 'close', lambda: None)
    monkeypatch.setattr('app.browser_tools.resolve_browser', lambda browser: 'C:/Chrome/chrome.exe')
    monkeypatch.setattr('app.browser_tools.subprocess.Popen', lambda argv, **kwargs: None)
    existing = {'hwnd': 11, 'executable': 'C:/Chrome/chrome.exe'}
    monkeypatch.setattr('app.browser_tools.list_visible_windows', lambda: [existing])
    monkeypatch.setattr('app.browser_tools.time.sleep', lambda seconds: None)
    result = session.search('joji')
    assert result['effect'] == 'unknown'
    assert result['new_window_visible'] is False


def test_navigation_waits_for_observed_page_not_blank_acceptance(monkeypatch):
    session = BrowserSession()
    monkeypatch.setattr(session, '_start', lambda: None)
    monkeypatch.setattr(session, '_run', lambda commands: [{}])
    monkeypatch.setattr('app.browser_tools.time.sleep', lambda seconds: None)
    pages = iter([{'url': 'about:blank', 'title': '', 'links': [], 'media': []},
                  {'url': 'https://www.youtube.com/results', 'title': 'Results',
                   'links': [{'index': 0, 'url': 'https://www.youtube.com/watch?v=fixture'}], 'media': []}])
    monkeypatch.setattr(session, 'inspect', lambda: next(pages))
    result = session.navigate('https://www.youtube.com/results')
    assert result['title'] == 'Results'
