import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routing import detect_deterministic_tools
from app.tools import ToolRegistry
from app.applications import resolve_browser


@pytest.mark.parametrize('command', [
    'open chrome and search github',
    'open chrome and seach github',
    'Open Chrome then search for github',
    'please open chrome and then look up github',
])
def test_browser_search_variants(command):
    assert detect_deterministic_tools(command) == [
        ('open_url', {'url': 'https://www.google.com/search?q=github', 'browser': 'chrome'})
    ]


def test_search_preserves_conjunctions():
    assert detect_deterministic_tools('open chrome and search cats and dogs')[0][1]['url'].endswith('cats+and+dogs')


def test_named_site_navigation_and_site_search():
    assert detect_deterministic_tools('open chrome and open github') == [
        ('open_url', {'url': 'https://github.com', 'browser': 'chrome'})
    ]
    assert detect_deterministic_tools('open edge and open github and search for tauri') == [
        ('open_url', {'url': 'https://github.com/search?q=tauri', 'browser': 'edge'})
    ]


@pytest.mark.parametrize('command', [
    'open chrome and something else',
    'open chrome and search github and send an email',
    'open chrome and check Gmail',
])
def test_underspecified_or_unsupported_steps_do_not_execute(command):
    assert detect_deterministic_tools(command) == []


def test_explicit_browser_uses_argument_list_not_default_browser(monkeypatch):
    launched = []
    monkeypatch.setattr('app.tools.resolve_browser', lambda _: 'C:/Apps/Chrome/chrome.exe')
    monkeypatch.setattr('app.tools.subprocess.Popen', lambda args, **kwargs: launched.append((args, kwargs)))
    monkeypatch.setattr('app.tools.webbrowser.open', lambda *_a, **_k: pytest.fail('Wrong browser'))
    url = 'https://www.google.com/search?q=github%26echo+hello'
    ToolRegistry().execute('open_url', {'url': url, 'browser': 'chrome'})
    assert launched == [(['C:/Apps/Chrome/chrome.exe', url], {'shell': False})]


def test_missing_browser_is_an_error(monkeypatch):
    for key in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA'):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr('app.applications.shutil.which', lambda _: None)
    with pytest.raises(RuntimeError, match='could not be located'):
        resolve_browser('chrome')


def test_exact_user_command_through_endpoint_and_tool(monkeypatch):
    launched = []
    monkeypatch.setattr('app.tools.resolve_browser', lambda _: 'C:/Apps/Chrome/chrome.exe')
    monkeypatch.setattr('app.tools.subprocess.Popen', lambda args, **kwargs: launched.append(args))
    response = TestClient(app).post('/api/command', json={'prompt': 'open chrome and seach github'})
    assert 'event: final' in response.text
    assert launched == [['C:/Apps/Chrome/chrome.exe', 'https://www.google.com/search?q=github']]
