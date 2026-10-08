"""Windows adaptation of OthersideAI's MIT-licensed PyAutoGUI input driver."""
import io
import threading
import time
import math
import sys
from uuid import uuid4
from app.accessibility import ObservationChangedError, read_targets

import pyautogui
from PIL import ImageDraw


class OperatingSystem:
    def __init__(self, cancelled=None):
        self.cancelled = cancelled or threading.Event()
        pyautogui.PAUSE = 0.01
        pyautogui.FAILSAFE = True
        self.capture_bounds = None
        self.capture_window = None
        self.capture_screen_size = None
        self.capture_scope = 'auto'
        self.targets = {}
        self.target_sources = {}

    def observe(self, scope):
        if scope not in {'screen', 'window'}:
            raise ValueError('Observation scope must be screen or window.')
        self.capture_scope = scope
        self.capture_bounds = None
        self.targets = {}
        self.target_sources = {}

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
        # A failed capture must never leave the previous targets actionable.
        self.capture_bounds = None
        self.targets = {}
        self.target_sources = {}
        before = self.window_state()
        screenshot = pyautogui.screenshot()
        after = self.window_state()
        if before != after:
            raise ObservationChangedError('Foreground changed during capture; retry observation.')
        width, height = screenshot.size
        if (width, height) != tuple(pyautogui.size()):
            raise RuntimeError('Screenshot and input dimensions disagree. Check Windows display scaling.')
        bounds = (0, 0, width, height)
        if after is not None and self.capture_scope in {'window', 'auto'}:
            _, left, top, window_width, window_height = after
            left, top, right, bottom = max(0, left), max(0, top), min(width, left + window_width), min(height, top + window_height)
            if right - left >= 200 and bottom - top >= 120:
                bounds = (left, top, right, bottom)
        self.capture_bounds, self.capture_window = bounds, after
        self.capture_screen_size = (width, height)
        self.targets = {}
        frame_id = uuid4().hex[:8]
        observed_targets = read_targets(after[0] if after else None)
        self.check()
        if self.window_state() != after or tuple(pyautogui.size()) != (width, height):
            self.capture_bounds = None
            raise ObservationChangedError('Desktop changed during target discovery; retry observation.')
        for item in observed_targets:
            rect = item.get('rect', [])
            if len(rect) != 4 or not all(isinstance(n, (int, float)) and math.isfinite(n) for n in rect):
                continue
            x, y, w, h = rect
            cx, cy = x + w / 2, y + h / 2
            left, top, right, bottom = bounds
            if w <= 0 or h <= 0 or not (left <= cx < right and top <= cy < bottom):
                continue
            key = f'{frame_id}-{len(self.targets)}'
            self.target_sources[key] = item
            self.targets[key] = {'id': key, 'marker': str(len(self.targets) + 1),
                                 'name': item.get('name', ''), 'role': item.get('role', ''),
                                 'x': round((cx-left)/(right-left-1), 6),
                                 'y': round((cy-top)/(bottom-top-1), 6)}
        screenshot = screenshot.crop(bounds)
        if screenshot.convert('RGB').getextrema() == ((0, 0), (0, 0), (0, 0)):
            raise RuntimeError('Desktop screenshot is black. Unlock Windows and run Wingent in your desktop session.')
        screenshot.thumbnail((1280, 1280))
        # Marks exist only in the model image, never on the user's actual desktop.
        draw = ImageDraw.Draw(screenshot)
        for target in self.targets.values():
            sx = round(target['x'] * (screenshot.width - 1))
            sy = round(target['y'] * (screenshot.height - 1))
            label = target['marker']
            box = draw.textbbox((0, 0), label)
            tw, th = box[2] - box[0] + 6, box[3] - box[1] + 6
            lx = max(0, min(screenshot.width - tw, sx + 5))
            ly = max(0, min(screenshot.height - th, sy - th - 3))
            draw.line((sx, sy, lx, ly + th), fill='#ffcc00', width=1)
            draw.rectangle((lx, ly, lx + tw, ly + th), fill='#111111', outline='#ffcc00')
            draw.text((lx + 3, ly + 3 - box[1]), label, fill='#ffcc00')
        output = io.BytesIO()
        screenshot.convert('RGB').save(output, format='PNG')
        return output.getvalue()

    def context(self):
        # Titles and read-only accessibility targets supplement the screenshot.
        window = self.window_state()
        return {'active_window': pyautogui.getActiveWindowTitle() or '',
                'window_id': window[0] if window else None,
                'coordinate_system': 'x,y fractions 0..1 of the supplied screenshot (possibly a foreground crop)',
                'screenshot_region': self.capture_bounds,
                'scope': 'screen' if self.capture_bounds == (0, 0, *(self.capture_screen_size or (0, 0))) else 'window',
                'targets': list(self.targets.values()),
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
                held.append(key)
                pyautogui.keyDown(key)
            self.wait(0.06)
        finally:
            # Low-level release bypasses the corner fail-safe so no key sticks.
            original_error = sys.exc_info()[1]
            release_error = None
            for key in reversed(held):
                try:
                    pyautogui.platformModule._keyUp(key)
                except Exception as exc:
                    release_error = release_error or exc
            if release_error is not None and original_error is None:
                raise release_error

    def mouse(self, detail):
        button, clicks = detail.get('button', 'left'), detail.get('clicks', 1)
        if button not in {'left', 'right', 'middle'} or type(clicks) is not int or clicks not in (1, 2):
            raise ValueError('Unsupported click gesture.')
        if clicks == 2 and button != 'left':
            raise ValueError('Double-click requires the left button.')
        # Some models copy a target's exact coordinates instead of its ID.
        # Ground only a unique, sub-pixel centre match; never snap a guessed
        # point to the nearest arbitrary control.
        if not detail.get('target_id') and self.capture_bounds is not None:
            left, top, right, bottom = self.capture_bounds
            matches = [key for key, target in self.targets.items()
                       if abs(target['x'] - float(detail['x'])) * (right-left-1) <= 1
                       and abs(target['y'] - float(detail['y'])) * (bottom-top-1) <= 1]
            if len(matches) == 1:
                detail = {**detail, 'target_id': matches[0]}
        if detail.get('target_id'):
            target = self.targets.get(detail['target_id'])
            if target is None:
                raise ValueError('Target is not from the current observation; observe again.')
            source = self.target_sources.get(detail['target_id'])
            if source is not None:
                self.validate_frame()
                current = read_targets(self.capture_window[0] if self.capture_window else None)
                matches = [item for item in current if (
                    item.get('runtime_id') == source['runtime_id'] if source.get('runtime_id') else
                    item.get('name') == source.get('name') and item.get('role') == source.get('role')
                    and item.get('rect') == source.get('rect'))]
                if (len(matches) != 1 or any(matches[0].get(key) != source.get(key)
                                             for key in ('name', 'role', 'rect'))):
                    raise RuntimeError('Observed control moved, changed, or disappeared; observe again before clicking.')
                self.validate_frame()
            detail = target
        self.click_at_percentage(float(detail['x']), float(detail['y']), button=button, clicks=clicks)

    def move(self, x, y):
        self.validate_frame()
        left, top, right, bottom = self.capture_bounds
        pyautogui.moveTo(left + round(x * (right - left - 1)),
                         top + round(y * (bottom - top - 1)), duration=0.12)
        self.validate_frame()

    def click_at_percentage(self, x_percentage, y_percentage, **kwargs):
        self.move(x_percentage, y_percentage)
        clicks = kwargs.get('clicks', 1)
        for index in range(clicks):
            if index:
                self.wait(0.08)
            self.validate_frame()
            pyautogui.click(button=kwargs.get('button', 'left'))

    def scroll(self, amount):
        self.validate_frame()
        pyautogui.scroll(amount)

    def wait(self, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.check()
            self.cancelled.wait(min(0.03, max(0, deadline - time.monotonic())))
