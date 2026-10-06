"""Mock Win32 only; never open search or send desktop input."""
from types import SimpleNamespace

from app import window_observer


class Function:
    def __init__(self, callback):
        self.callback = callback

    def __call__(self, *args):
        return self.callback(*args)


def test_foreground_search_is_inspected_even_when_enumwindows_omits_it(monkeypatch):
    queried = []

    def pid(hwnd, target):
        target._obj.value = hwnd
        return 1

    def image(handle, flags, buffer, size):
        queried.append(handle)
        buffer.value = 'SearchHost.exe' if handle == 42 else 'notepad.exe'
        return True

    def title(hwnd, buffer, size):
        buffer.value = '' if hwnd == 42 else 'Document'
        return len(buffer.value)

    user = SimpleNamespace(
        EnumWindows=Function(lambda callback, data: callback(7, data)),
        IsWindowVisible=Function(lambda hwnd: True),
        GetWindowTextLengthW=Function(lambda hwnd: 0 if hwnd == 42 else 8),
        GetWindowTextW=Function(title), GetWindowThreadProcessId=Function(pid))
    kernel = SimpleNamespace(OpenProcess=Function(lambda access, inherit, pid: pid),
        QueryFullProcessImageNameW=Function(image), CloseHandle=Function(lambda handle: True))
    monkeypatch.setattr(window_observer, 'os', SimpleNamespace(name='nt'))
    monkeypatch.setattr(window_observer, 'foreground_window_id', lambda: 42)
    monkeypatch.setattr(window_observer.ctypes, 'WinDLL', lambda name, **kw: user if name == 'user32' else kernel)
    windows = window_observer.list_visible_windows()
    assert windows[0] == {'hwnd': 42, 'pid': 42, 'title': '',
                          'process': 'SearchHost.exe', 'executable': 'SearchHost.exe'}
    assert queried == [42, 7]

    # If enumeration does include foreground, do not duplicate it.
    user.EnumWindows = Function(lambda callback, data: callback(42, data))
    assert len(window_observer.list_visible_windows()) == 1
