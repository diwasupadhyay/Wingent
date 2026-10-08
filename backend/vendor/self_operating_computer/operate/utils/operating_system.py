"""Windows adaptation of OthersideAI's MIT-licensed PyAutoGUI input driver."""
import io
import threading
import time

import pyautogui


class OperatingSystem:
    def __init__(self, cancelled=None):
        self.cancelled = cancelled or threading.Event()
        pyautogui.PAUSE = 0.01
        pyautogui.FAILSAFE = True
        self.capture_bounds = None
        self.capture_window = None
        self.capture_screen_size = None

    def window_state(self):
        window = pyautogui.getActiveWindow()
        if window is None:
            return None
        return (window._hWnd, window.left, window.top, window.width, window.height)

    def validate_frame(self):
        self.check()
        if self.capture_bounds is None:
            raise RuntimeError('Observe the screen before sending input.')
        if tuple(pyautogui.size()) != self.capture_screen_size:
            raise RuntimeError('Screen geometry changed; observe again before input.')
        if self.window_state() != self.capture_window:
            raise RuntimeError('Foreground window or geometry changed; observe again before input.')

    def check(self):
        if self.cancelled.is_set():
            raise InterruptedError('Computer control stopped.')
        pyautogui.failSafeCheck()

    def screenshot(self):
        self.check()
        before = self.window_state()
        screenshot = pyautogui.screenshot()
        after = self.window_state()
        if before != after:
            raise RuntimeError('Foreground changed during capture; retry observation.')
        width, height = screenshot.size
        if (width, height) != tuple(pyautogui.size()):
            raise RuntimeError('Screenshot and input dimensions disagree. Check Windows display scaling.')
        bounds = (0, 0, width, height)
        if after is not None:
            _, left, top, window_width, window_height = after
            left, top, right, bottom = max(0, left), max(0, top), min(width, left + window_width), min(height, top + window_height)
            if right - left >= 200 and bottom - top >= 120:
                bounds = (left, top, right, bottom)
        self.capture_bounds, self.capture_window = bounds, after
        self.capture_screen_size = (width, height)
        screenshot = screenshot.crop(bounds)
        if screenshot.convert('RGB').getextrema() == ((0, 0), (0, 0), (0, 0)):
            raise RuntimeError('Desktop screenshot is black. Unlock Windows and run Wingent in your desktop session.')
        screenshot.thumbnail((1280, 1280))
        output = io.BytesIO()
        screenshot.convert('RGB').save(output, format='PNG')
        return output.getvalue()

    def context(self):
        # Native window titles are cheap hints; screenshots remain the input
        # authority. No UIA process or window-grant workflow is involved.
        return {'active_window': pyautogui.getActiveWindowTitle() or '',
                'coordinate_system': 'x,y fractions 0..1 of the supplied screenshot (possibly a foreground crop)',
                'screenshot_region': self.capture_bounds,
                'open_windows': [title for title in pyautogui.getAllTitles() if title.strip()][:24]}

    def write(self, content):
        # Real key events are needed by apps that handle keyboard shortcuts
        # rather than WM_CHAR (including Calculator). Unicode is a fallback.
        from app.unicode_input import type_code_unit
        self.validate_frame()
        for char in content.replace('\r\n', '\n'):
            self.validate_frame()
            if char in '\n\r\t':
                self.press(['tab' if char == '\t' else 'enter'])
            elif char.isascii():
                pyautogui.write(char, _pause=False)
            else:
                encoded = char.encode('utf-16-le')
                for offset in range(0, len(encoded), 2):
                    type_code_unit(int.from_bytes(encoded[offset:offset + 2], 'little'))
            self.cancelled.wait(0.005)

    def press(self, keys):
        self.validate_frame()
        aliases = {'control': 'ctrl', 'return': 'enter', 'escape': 'esc',
                   'windows': 'win', 'page_down': 'pagedown', 'page_up': 'pageup'}
        keys = [aliases.get(key.lower(), key.lower()) for key in keys]
        if any(key not in pyautogui.KEYBOARD_KEYS for key in keys):
            raise ValueError('Unknown keyboard key: ' + repr(keys))
        held = []
        try:
            for key in keys:
                self.check()
                pyautogui.keyDown(key)
                held.append(key)
            self.wait(0.06)
        finally:
            # Low-level release bypasses the corner fail-safe so no key sticks.
            for key in reversed(held):
                pyautogui.platformModule._keyUp(key)

    def mouse(self, detail):
        self.click_at_percentage(float(detail['x']), float(detail['y']))

    def move(self, x, y):
        self.validate_frame()
        left, top, right, bottom = self.capture_bounds
        pyautogui.moveTo(left + round(x * (right - left - 1)),
                         top + round(y * (bottom - top - 1)), duration=0.12)
        self.validate_frame()

    def click_at_percentage(self, x_percentage, y_percentage, **kwargs):
        self.move(x_percentage, y_percentage)
        pyautogui.click()

    def scroll(self, amount):
        self.validate_frame()
        pyautogui.scroll(amount)

    def wait(self, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.check()
            self.cancelled.wait(min(0.03, max(0, deadline - time.monotonic())))
