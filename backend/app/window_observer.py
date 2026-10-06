"""Read-only Win32 enumeration of visible top-level windows."""

import ctypes
import os
from ctypes import wintypes
from pathlib import Path

from app.capabilities import Arguments
from app.tools import ToolPermission


def is_agent_window(window):
    """The command overlay is never an application input target."""
    return window.get('title', '').casefold().startswith('wingent') and window.get('process', '').casefold() in {'app.exe', 'wingent.exe'}


def foreground_window_id():
    if os.name != 'nt':
        return None
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    user32.GetForegroundWindow.restype = wintypes.HWND
    return int(user32.GetForegroundWindow() or 0) or None


def list_visible_windows(limit=40):
    if os.name != 'nt':
        return []
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                                     wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    windows = []
    foreground = foreground_window_id()
    seen = set()

    def inspect(hwnd, unused):
        if not hwnd or int(hwnd) in seen:
            return True
        seen.add(int(hwnd))
        if not user32.IsWindowVisible(hwnd):
            return True
        title_length = min(user32.GetWindowTextLengthW(hwnd), 300)
        # Windows Search can own an untitled foreground window. Its verified
        # process identity remains useful even without a caption.
        if title_length < 1 and int(hwnd) != foreground:
            return True
        title = ctypes.create_unicode_buffer(title_length + 1)
        user32.GetWindowTextW(hwnd, title, len(title))
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        handle = kernel32.OpenProcess(0x1000, False, pid.value)
        if not handle:
            return True
        try:
            executable = ctypes.create_unicode_buffer(32768)
            size = wintypes.DWORD(len(executable))
            if kernel32.QueryFullProcessImageNameW(handle, 0, executable, ctypes.byref(size)):
                window = {'title': title.value, 'process': Path(executable.value).name,
                          'executable': executable.value, 'pid': pid.value, 'hwnd': int(hwnd)}
                if not is_agent_window(window):
                    windows.append(window)
        finally:
            kernel32.CloseHandle(handle)
        return len(windows) < limit

    # EnumWindows does not reliably enumerate modern shell/UWP surfaces.
    # Inspect the actual foreground HWND directly before the desktop list;
    # retain the same visibility and executable-identity checks.
    if foreground:
        inspect(foreground, 0)
    user32.EnumWindows(callback_type(inspect), 0)
    return windows


def visible_window_for_executable(executable: str) -> bool:
    expected = os.path.normcase(os.path.abspath(executable))
    return any(os.path.normcase(item['executable']) == expected for item in list_visible_windows())


def register(registry):
    def observe(_):
        windows = list_visible_windows()
        foreground = foreground_window_id()
        observed_foreground = foreground if any(item['hwnd'] == foreground for item in windows) else 0
        return {'ok': True, 'windows': [
            {'title': item['title'], 'process': item['process'], 'pid': item['pid'],
             'window_id': item['hwnd'], 'is_foreground': item['hwnd'] == observed_foreground}
            for item in windows], 'truncated': len(windows) >= 40,
            'foreground_window_id': observed_foreground,
            'observation': 'Visible top-level windows and foreground identity at capture time (0 means unlisted); no page-content or pixel understanding.'}
    registry.register('observe_windows', 'List visible top-level Windows windows, with process/title and current foreground window.',
                      ToolPermission.SAFE, {}, observe, input_model=Arguments,
                      capability='windows', timeout_seconds=10, retry_safe=True)
