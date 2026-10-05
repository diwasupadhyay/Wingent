"""Opt-in native gesture check in a disposable unfamiliar canvas; no app workflow in runtime."""
import argparse
import ctypes
import json
import subprocess
import sys
import time
import tkinter as tk
from ctypes import wintypes

from app import windows_computer as native
from app.computer_tools import ComputerSession
from app.tools import execution_task_id


def fixture():
    root = tk.Tk()
    root.title('Wingent isolated gesture evaluation')
    root.geometry('600x400+100+100')
    canvas = tk.Canvas(root, background='white', highlightthickness=0)
    canvas.pack(fill='both', expand=True)
    dragging = False
    hovered = False

    def motion(event):
        nonlocal hovered
        if not hovered and abs(event.x / canvas.winfo_width() - .2) < .08:
            hovered = True
            print(json.dumps({'hovered': True}), flush=True)

    def press(event):
        nonlocal dragging
        dragging = abs(event.x / canvas.winfo_width() - .2) < .08

    def release(event):
        print(json.dumps({'dragged': dragging and abs(event.x / canvas.winfo_width() - .75) < .08}), flush=True)

    def paint(_):
        canvas.delete('all')
        width, height = canvas.winfo_width(), canvas.winfo_height()
        canvas.create_rectangle(width*.15, height*.4, width*.25, height*.6, fill='steelblue')
        canvas.create_rectangle(width*.7, height*.4, width*.8, height*.6, outline='green', width=4)
    canvas.bind('<Configure>', paint)
    canvas.bind('<Motion>', motion)
    canvas.bind('<ButtonPress-1>', press)
    canvas.bind('<ButtonRelease-1>', release)
    root.after(200, root.focus_force)
    root.mainloop()


def run():
    child = subprocess.Popen([sys.executable, __file__, '--fixture'], stdout=subprocess.PIPE, text=True)
    token = execution_task_id.set('gesture-evaluation')
    session = ComputerSession()
    try:
        deadline = time.monotonic() + 10
        window = None
        while time.monotonic() < deadline:
            window = next((w for w in native.list_visible_windows() if w['pid'] == child.pid), None)
            if window:
                break
            time.sleep(.1)
        if not window:
            raise RuntimeError('Owned fixture did not appear')
        time.sleep(.4)  # Let this newly created fixture finish its own focus setup.
        frame = session.begin(window_id=window['hwnd'], purpose='Check isolated canvas gestures')
        api = native.user32()
        old = api.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
        try:
            client, origin = wintypes.RECT(), wintypes.POINT(0, 0)
            api.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
            api.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
            if not api.GetClientRect(window['hwnd'], ctypes.byref(client)) or not api.ClientToScreen(window['hwnd'], ctypes.byref(origin)):
                raise RuntimeError('Fixture geometry unavailable')
        finally:
            api.SetThreadDpiAwarenessContext(old)
        rect = native.rectangle(window['hwnd'])
        def point(fraction):
            return (round((origin.x + client.right*fraction - rect[0])*1000/(rect[2]-1)),
                    round((origin.y + client.bottom*.5 - rect[1])*1000/(rect[3]-1)))
        x, y = point(.2)
        end_x, end_y = point(.75)
        for action in [dict(kind='hover', x=x, y=y, duration_ms=200),
                       dict(kind='drag', x=x, y=y, end_x=end_x, end_y=end_y, duration_ms=400),
                       dict(kind='wait', duration_ms=300)]:
            # Only this disposable canvas's drag is approved by the harness.
            result = session.act(_confirmed=action['kind'] == 'drag', frame_id=frame['frame_id'], **action)
            if not result['ok'] or not result['post_observation']['ok']:
                raise RuntimeError(str(result))
            frame = result['post_observation']
        child.terminate()
        output, _ = child.communicate(timeout=5)
        passed = '"hovered": true' in output and '"dragged": true' in output
        print(json.dumps({'gesture_oracle_passed': passed, 'app_output': output.strip(), 'fresh_wait_frame': bool(frame['frame_id'])}), flush=True)
        if not passed:
            raise RuntimeError('Canvas did not record the expected pointer effects')
    finally:
        session.close_task('gesture-evaluation')
        execution_task_id.reset(token)
        if child.poll() is None:
            child.terminate()
        child.wait(timeout=5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixture', action='store_true')
    args = parser.parse_args()
    fixture() if args.fixture else run()
