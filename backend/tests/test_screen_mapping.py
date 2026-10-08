from types import SimpleNamespace
import pytest
from PIL import Image
import pyautogui
from vendor.self_operating_computer.operate.utils.operating_system import OperatingSystem


def driver(monkeypatch):
    window = SimpleNamespace(_hWnd=5, left=200, top=100, width=600, height=400)
    monkeypatch.setattr(pyautogui, 'getActiveWindow', lambda: window)
    monkeypatch.setattr(pyautogui, 'size', lambda: (1920, 1080))
    monkeypatch.setattr(pyautogui, 'screenshot', lambda: Image.new('RGB', (1920, 1080), 'white'))
    desktop = OperatingSystem()
    monkeypatch.setattr(desktop, 'check', lambda: None)
    return desktop, window


def test_crop_coordinates_map_to_physical_screen(monkeypatch):
    desktop, _ = driver(monkeypatch)
    moved = []
    monkeypatch.setattr(pyautogui, 'moveTo', lambda x, y, **kw: moved.append((x, y)))
    desktop.screenshot()
    assert desktop.capture_bounds == (200, 100, 800, 500)
    desktop.move(0, 0)
    desktop.move(1, 1)
    assert moved == [(200, 100), (799, 499)]


def test_moved_window_is_rejected_before_mouse_input(monkeypatch):
    desktop, window = driver(monkeypatch)
    desktop.screenshot()
    window.left += 10
    monkeypatch.setattr(pyautogui, 'moveTo', lambda *a, **kw: pytest.fail('Must not move'))
    with pytest.raises(RuntimeError, match='Foreground window or geometry changed'):
        desktop.move(0.5, 0.5)


def test_capture_refuses_dimension_mismatch(monkeypatch):
    desktop, _ = driver(monkeypatch)
    monkeypatch.setattr(pyautogui, 'size', lambda: (1280, 720))
    with pytest.raises(RuntimeError, match='dimensions disagree'):
        desktop.screenshot()


def test_typing_stops_if_focus_changes_mid_input(monkeypatch):
    desktop, window = driver(monkeypatch)
    desktop.screenshot()
    written = []
    def write(text, **kwargs):
        written.append(text)
        window._hWnd = 9
    monkeypatch.setattr(pyautogui, 'write', write)
    with pytest.raises(RuntimeError, match='Foreground'):
        desktop.write('abc')
    assert written == ['a']
