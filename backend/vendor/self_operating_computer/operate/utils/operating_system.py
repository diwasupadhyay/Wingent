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

    def check(self):
        if self.cancelled.is_set():
            raise InterruptedError('Computer control stopped.')
        pyautogui.failSafeCheck()

    def screenshot(self):
        self.check()
        screenshot = pyautogui.screenshot()
        if screenshot.convert('RGB').getextrema() == ((0, 0), (0, 0), (0, 0)):
            raise RuntimeError('Desktop screenshot is black. Unlock Windows and run Wingent in your desktop session.')
        screenshot.thumbnail((1280, 1280))
        output = io.BytesIO()
        screenshot.convert('RGB').save(output, format='PNG')
        return output.getvalue()

    def write(self, content):
        # Unicode input avoids clipboard replacement and keyboard-layout loss.
        from app.unicode_input import type_code_unit
        encoded = content.encode('utf-16-le')
        for offset in range(0, len(encoded), 2):
            self.check()
            code = int.from_bytes(encoded[offset:offset + 2], 'little')
            if code in (10, 13, 9):
                self.press(['enter' if code in (10, 13) else 'tab'])
            else:
                type_code_unit(code)

    def press(self, keys):
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
        self.check()
        width, height = pyautogui.size()
        pyautogui.moveTo(round(x * (width - 1)), round(y * (height - 1)), duration=0.2)
        self.check()

    def click_at_percentage(self, x_percentage, y_percentage, **kwargs):
        self.move(x_percentage, y_percentage)
        pyautogui.click()

    def scroll(self, amount):
        self.check()
        pyautogui.scroll(amount)

    def wait(self, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.check()
            self.cancelled.wait(min(0.03, max(0, deadline - time.monotonic())))
