"""Bounded Win32 control observation and approved, target-bound input.

This is not screenshot understanding or a universal accessibility implementation.
Only a recently observed, still-identical visible window/control can be targeted.
"""

import ctypes
import os
import threading
import time
from ctypes import wintypes

from typing import Literal

from pydantic import Field

from app.capabilities import Arguments
from app.tools import ToolPermission
from app.window_observer import foreground_window_id, list_visible_windows


class ObserveTarget(Arguments):
    window_id: int = Field(gt=0)


class ClickTarget(ObserveTarget):
    control_id: int = Field(gt=0)
    observation_id: int = Field(gt=0)


class TypeTarget(ClickTarget):
    text: str = Field(min_length=1, max_length=500)


class KeyTarget(ObserveTarget):
    observation_id: int = Field(gt=0)
    key: Literal['enter', 'escape', 'tab', 'shift_tab', 'space', 'up', 'down',
                 'left', 'right', 'home', 'end', 'page_up', 'page_down']


def _user32():
    if os.name != 'nt':
        raise RuntimeError('Desktop control requires an interactive Windows session.')
    return ctypes.WinDLL('user32', use_last_error=True)


def _control_snapshot(window_id):
    user32 = _user32()
    user32.IsWindow.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.EnumChildWindows.argtypes = [wintypes.HWND, ctypes.c_void_p, wintypes.LPARAM]
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    if not user32.IsWindow(window_id) or not user32.IsWindowVisible(window_id):
        raise ValueError('The selected window is no longer visible.')
    controls = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def collect(hwnd, unused):
        if len(controls) >= 60:
            return False
        if not user32.IsWindowVisible(hwnd):
            return True
        kind = ctypes.create_unicode_buffer(128)
        user32.GetClassNameW(hwnd, kind, len(kind))
        # Never reveal password-edit contents to the model.
        password = kind.value.casefold() == 'edit' and bool(user32.GetWindowLongW(hwnd, -16) & 0x20)
        length = min(user32.GetWindowTextLengthW(hwnd), 160)
        label = ctypes.create_unicode_buffer(length + 1)
        if not password and length:
            user32.GetWindowTextW(hwnd, label, len(label))
        rect = wintypes.RECT()
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)) and rect.right > rect.left and rect.bottom > rect.top:
            controls.append({'control_id': int(hwnd), 'class': kind.value,
                             'text': '[password field]' if password else label.value,
                             'rect': [rect.left, rect.top, rect.right, rect.bottom],
                             'password': password})
        return True

    user32.EnumChildWindows(window_id, callback_type(collect), 0)
    return controls


class DesktopSession:
    def __init__(self, snapshot=_control_snapshot, windows=list_visible_windows,
                 clock=time.monotonic, click=None, type_text=None, press_key=None,
                 foreground=foreground_window_id):
        self.snapshot = snapshot
        self.windows = windows
        self.clock = clock
        self.click_dispatch = click or _click
        self.type_dispatch = type_text or _type_text
        self.key_dispatch = press_key or _press_key
        self.foreground = foreground
        self.lock = threading.RLock()
        self.last = None
        self.sequence = 0

    def observe(self, window_id):
        with self.lock:
            match = next((w for w in self.windows() if w['hwnd'] == window_id), None)
            if not match:
                self.last = None
                return {'ok': False, 'effect': 'no_effect', 'reason': 'Window is not currently visible.'}
            controls = self.snapshot(window_id)
            self.sequence += 1
            self.last = {'id': self.sequence, 'at': self.clock(), 'window': match,
                         'controls': {c['control_id']: c for c in controls}}
            return {'ok': True, 'window_id': window_id, 'observation_id': self.sequence,
                    'process': match['process'], 'title': match['title'],
                    'is_foreground': self.foreground() == window_id,
                    'controls': controls, 'truncated': len(controls) >= 60,
                    'limitation': 'Win32 child controls only; browser and canvas contents are not visible.'}

    def _target(self, window_id, control_id, observation_id):
        self._target_window(window_id, observation_id)
        prior = self.last
        old = prior['controls'].get(control_id)
        new = next((c for c in self.snapshot(window_id) if c['control_id'] == control_id), None)
        if not old or not new or any(old[k] != new[k] for k in ('class', 'text', 'rect', 'password')):
            raise ValueError('Control changed; observe again.')
        if old['password']:
            raise ValueError('Password controls require direct user interaction.')
        return new

    def _target_window(self, window_id, observation_id, max_age=10):
        prior = self.last
        if not prior or prior['id'] != observation_id or prior['window']['hwnd'] != window_id:
            raise ValueError('Target is not from the latest desktop observation.')
        if self.clock() - prior['at'] > max_age:
            raise ValueError('Desktop observation is stale; observe again.')
        current = next((w for w in self.windows() if w['hwnd'] == window_id), None)
        if not current or any(current[k] != prior['window'][k] for k in ('pid', 'executable', 'title')):
            raise ValueError('Window identity changed; observe again.')
        return current

    def window_identity(self, window_id, observation_id, max_age=10):
        with self.lock:
            current = self._target_window(window_id, observation_id, max_age=max_age).copy()
            current['password_controls_present'] = any(
                control['password'] for control in self.last['controls'].values())
            return current

    def press_key(self, window_id, observation_id, key):
        with self.lock:
            try:
                self._target_window(window_id, observation_id)
            except ValueError as exc:
                return {'ok': False, 'effect': 'no_effect', 'reason': str(exc)}
            self.last = None
            self.key_dispatch(window_id, key)
            return {'ok': True, 'effect': 'accepted',
                    'reason': 'Key dispatched to the selected window; whole-goal effect not verified.',
                    'post_observation': self._post_observe(window_id)}

    def click(self, window_id, control_id, observation_id):
        with self.lock:
            try:
                control = self._target(window_id, control_id, observation_id)
            except ValueError as exc:
                return {'ok': False, 'effect': 'no_effect', 'reason': str(exc)}
            self.last = None
            self.click_dispatch(window_id, control_id, control['rect'])
            return {'ok': True, 'effect': 'accepted',
                    'reason': 'Click dispatched; whole-goal effect not verified.',
                    'post_observation': self._post_observe(window_id)}

    def type_text(self, window_id, control_id, observation_id, text):
        with self.lock:
            try:
                control = self._target(window_id, control_id, observation_id)
                if control['class'].casefold() not in {'edit', 'richedit20w', 'richedit50w'}:
                    raise ValueError('Selected control is not a recognized text input.')
            except ValueError as exc:
                return {'ok': False, 'effect': 'no_effect', 'reason': str(exc)}
            self.last = None
            self.type_dispatch(window_id, control_id, text)
            return {'ok': True, 'effect': 'accepted',
                    'reason': 'Text input dispatched; whole-goal effect not verified.',
                    'post_observation': self._post_observe(window_id)}

    def _post_observe(self, window_id):
        # A control can disappear after a valid click. Preserve the dispatch result
        # and expose the changed/closed window instead of pretending nothing happened.
        time.sleep(0.15)
        try:
            observation = self.observe(window_id)
        except (OSError, ValueError, RuntimeError) as exc:
            return {'ok': False, 'reason': f'Post-action observation failed: {type(exc).__name__}.'}
        if observation.get('ok'):
            return {**observation, 'controls': observation['controls'][:12],
                    'truncated': observation['truncated'] or len(observation['controls']) > 12}
        return observation


def _focus_control(window_id, control_id):
    user32 = _user32()
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.SetFocus.argtypes = [wintypes.HWND]
    if not user32.SetForegroundWindow(window_id) or user32.GetForegroundWindow() != window_id:
        raise RuntimeError('Could not focus the target window; no input was dispatched.')
    user32.SetFocus(control_id)


def _press_key(window_id, key):
    codes = {'enter': 0x0D, 'escape': 0x1B, 'tab': 0x09, 'space': 0x20,
             'up': 0x26, 'down': 0x28, 'left': 0x25, 'right': 0x27,
             'home': 0x24, 'end': 0x23, 'page_up': 0x21, 'page_down': 0x22}
    user32 = _user32()
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.GetForegroundWindow.restype = wintypes.HWND
    if not user32.SetForegroundWindow(window_id) or user32.GetForegroundWindow() != window_id:
        raise RuntimeError('Could not focus the target window; no key was dispatched.')

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [('wVk', wintypes.WORD), ('wScan', wintypes.WORD),
                    ('dwFlags', wintypes.DWORD), ('time', wintypes.DWORD),
                    ('dwExtraInfo', ctypes.c_size_t)]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [('dx', wintypes.LONG), ('dy', wintypes.LONG),
                    ('mouseData', wintypes.DWORD), ('dwFlags', wintypes.DWORD),
                    ('time', wintypes.DWORD), ('dwExtraInfo', ctypes.c_size_t)]

    class INPUTUNION(ctypes.Union):
        _fields_ = [('ki', KEYBDINPUT), ('mi', MOUSEINPUT)]

    class INPUT(ctypes.Structure):
        _fields_ = [('type', wintypes.DWORD), ('data', INPUTUNION)]

    sequence = [0x10, codes.get(key, 0x09)] if key == 'shift_tab' else [codes[key]]
    events = [INPUT(1, INPUTUNION(ki=KEYBDINPUT(code, 0, 0, 0, 0))) for code in sequence]
    events.extend(INPUT(1, INPUTUNION(ki=KEYBDINPUT(code, 0, 0x0002, 0, 0)))
                  for code in reversed(sequence))
    user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
    user32.SendInput.restype = wintypes.UINT
    batch = (INPUT * len(events))(*events)
    sent = user32.SendInput(len(events), batch, ctypes.sizeof(INPUT))
    if sent != len(events):
        raise RuntimeError('Key input was only partly dispatched; effect is unknown.')


def _click(window_id, control_id, rect):
    _focus_control(window_id, control_id)
    user32 = _user32()
    user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
    x, y = (rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2
    if not user32.SetCursorPos(x, y):
        raise RuntimeError('Could not position pointer; click was not dispatched.')
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    user32.mouse_event(0x0004, 0, 0, 0, 0)


def _type_text(window_id, control_id, text):
    if any(ord(char) < 32 and char not in '\r\n\t' for char in text):
        raise ValueError('Control characters are not accepted for desktop typing.')
    _focus_control(window_id, control_id)
    user32 = _user32()
    user32.SendMessageTimeoutW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM,
                                           wintypes.LPARAM, wintypes.UINT, wintypes.UINT,
                                           ctypes.POINTER(ctypes.c_size_t)]
    # WM_CHAR targets the observed control, avoiding global typing into a different app.
    for char in text:
        result = ctypes.c_size_t()
        if not user32.SendMessageTimeoutW(control_id, 0x0102, ord(char), 0, 0x0002, 300,
                                          ctypes.byref(result)):
            raise RuntimeError('Desktop text dispatch stopped; some characters may have been entered.')


def register(registry, session=None):
    session = session or DesktopSession()
    registry.register('desktop_observe', 'Observe Win32 child controls of a visible window_id returned by observe_windows.',
                      ToolPermission.SAFE, {}, lambda p: session.observe(**p),
                      input_model=ObserveTarget, capability='windows', timeout_seconds=10, retry_safe=True)
    registry.register('desktop_click_control', 'Click a freshly observed control in the same visible window; result remains unverified.',
                      ToolPermission.CONFIRMATION_REQUIRED, {}, lambda p: session.click(**p),
                      input_model=ClickTarget, capability='windows', timeout_seconds=10)
    registry.register('desktop_type_text', 'Type up to 500 characters into a freshly observed non-password Win32 Edit control.',
                      ToolPermission.CONFIRMATION_REQUIRED, {}, lambda p: session.type_text(**p),
                      input_model=TypeTarget, capability='windows', timeout_seconds=10)
    registry.register('desktop_press_key', 'Press one navigation or activation key in a freshly observed visible window; observe the result.',
                      ToolPermission.CONFIRMATION_REQUIRED, {}, lambda p: session.press_key(**p),
                      input_model=KeyTarget, capability='windows', timeout_seconds=10)
    return session
