from app.tools import ToolRegistry
from app.window_observer import register, visible_window_for_executable


def test_window_observer_exposes_bounded_read_only_fields(monkeypatch):
    monkeypatch.setattr('app.window_observer.list_visible_windows', lambda limit=40: [
        {'title': 'Example', 'process': 'chrome.exe', 'executable': 'C:/Chrome/chrome.exe',
         'pid': 123, 'hwnd': 45},
    ])
    registry = ToolRegistry()
    register(registry)
    result = registry.execute('observe_windows', {})
    assert result['windows'] == [{'title': 'Example', 'process': 'chrome.exe',
                                  'pid': 123, 'window_id': 45}]
    assert 'executable' not in result['windows'][0]
    assert visible_window_for_executable('C:/Chrome/chrome.exe') is True
