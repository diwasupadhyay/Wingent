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
    monkeypatch.setattr('vendor.self_operating_computer.operate.utils.operating_system.read_targets', lambda _: [])
    monkeypatch.setattr(desktop, 'check', lambda: None)
    return desktop, window


def test_crop_coordinates_map_to_physical_screen(monkeypatch):
    desktop, _ = driver(monkeypatch)
    desktop.observe('window')
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


def test_full_screen_is_default_and_observed_target_maps_exactly(monkeypatch):
    desktop, _ = driver(monkeypatch)
    monkeypatch.setattr('vendor.self_operating_computer.operate.utils.operating_system.read_targets',
        lambda _: [{'name': 'Example control', 'role': 'ControlType.Button', 'rect': [310, 220, 80, 40]}])
    clicks = []
    monkeypatch.setattr(pyautogui, 'moveTo', lambda x, y, **kwargs: clicks.append((x, y)))
    monkeypatch.setattr(pyautogui, 'click', lambda **kwargs: None)
    desktop.screenshot()
    assert desktop.capture_bounds == (0, 0, 1920, 1080)
    target_id = next(iter(desktop.targets))
    desktop.mouse({'target_id': target_id})
    assert clicks == [(350, 240)]
    desktop.screenshot()
    with pytest.raises(ValueError, match='current observation'):
        desktop.mouse({'target_id': target_id})


def test_accessibility_unavailable_keeps_visual_fallback(monkeypatch):
    desktop, _ = driver(monkeypatch)
    desktop.screenshot()
    assert desktop.targets == {}
    assert desktop.capture_bounds == (0, 0, 1920, 1080)


@pytest.mark.parametrize('gesture', [{'button': 'right'}, {'clicks': 2}])
def test_target_id_keeps_click_gesture(monkeypatch, gesture):
    desktop, _ = driver(monkeypatch)
    desktop.screenshot()
    desktop.targets['test-id'] = {'x': .5, 'y': .5}
    monkeypatch.setattr(desktop, 'move', lambda *args: None)
    calls = []
    monkeypatch.setattr(pyautogui, 'click', lambda **kwargs: calls.append(kwargs))
    desktop.mouse({'target_id': 'test-id', **gesture})
    assert calls == [{'button': gesture.get('button', 'left')}] * gesture.get('clicks', 1)


def test_stop_between_double_clicks_prevents_second_click(monkeypatch):
    desktop, _ = driver(monkeypatch)
    desktop.screenshot()
    monkeypatch.setattr(desktop, 'move', lambda *args: None)
    clicks = []
    def click(**kwargs):
        clicks.append(kwargs)
        desktop.cancelled.set()
    def check():
        if desktop.cancelled.is_set():
            raise InterruptedError('Stopped')
    monkeypatch.setattr(desktop, 'check', check)
    monkeypatch.setattr(pyautogui, 'click', click)
    with pytest.raises(InterruptedError):
        desktop.mouse({'x': .5, 'y': .5, 'clicks': 2})
    assert len(clicks) == 1


def test_partial_key_down_failure_still_releases_key(monkeypatch):
    desktop, _ = driver(monkeypatch)
    desktop.screenshot()
    releases = []
    def fail(key):
        raise RuntimeError('Partial key down')
    monkeypatch.setattr(pyautogui, 'keyDown', fail)
    monkeypatch.setattr(pyautogui.platformModule, '_keyUp', releases.append)
    with pytest.raises(RuntimeError, match='Partial key down'):
        desktop.press(['ctrl', 'a'])
    assert releases == ['ctrl']


def test_key_release_failure_does_not_skip_remaining_modifiers(monkeypatch):
    desktop, _ = driver(monkeypatch)
    desktop.screenshot()
    releases = []
    monkeypatch.setattr(pyautogui, 'keyDown', lambda key: None)
    def release(key):
        releases.append(key)
        if key == 'a':
            raise RuntimeError('Release failed')
    monkeypatch.setattr(pyautogui.platformModule, '_keyUp', release)
    with pytest.raises(RuntimeError, match='Release failed'):
        desktop.press(['ctrl', 'shift', 'a'])
    assert releases == ['a', 'shift', 'ctrl']


def test_window_switch_during_target_discovery_invalidates_frame(monkeypatch):
    from app.accessibility import ObservationChangedError
    desktop, window = driver(monkeypatch)
    desktop.screenshot()
    def discover(_):
        window._hWnd = 99
        return [{'name': 'Stale', 'rect': [300, 200, 40, 40]}]
    monkeypatch.setattr('vendor.self_operating_computer.operate.utils.operating_system.read_targets', discover)
    with pytest.raises(ObservationChangedError, match='target discovery'):
        desktop.screenshot()
    assert desktop.capture_bounds is None
    assert desktop.targets == {}
    with pytest.raises(RuntimeError, match='Observe the screen'):
        desktop.move(.5, .5)
