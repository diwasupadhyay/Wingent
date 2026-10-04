"""Interactive adapter integration checks in disposable Notepad and Calculator windows.

No LLM scripts or app workflows are installed in the agent. These are test cases.
Refuses to reuse pre-existing windows. Creates one uniquely named scratch file.
"""
import ctypes
import json
import subprocess
import time
from pathlib import Path
from uuid import uuid4
from ctypes import wintypes

from app import windows_computer as native
from app.computer_tools import ComputerSession
from app.tools import execution_task_id


def new_window(before, predicate):
    until = time.monotonic() + 15
    while time.monotonic() < until:
        found = next((w for w in native.list_visible_windows() if w['hwnd'] not in before and predicate(w)), None)
        if found: return found
        time.sleep(.2)
    raise RuntimeError('No new matching window appeared; pre-existing windows were not touched.')


def run():
    session = ComputerSession()
    token = execution_task_id.set('native-smoke')
    owned = []
    try:
        scratch = Path('.build') / ('wingent-test-' + uuid4().hex[:8] + '.txt')
        scratch.parent.mkdir(exist_ok=True)
        with scratch.open('x', encoding='utf-8') as file:
            file.write('Wingent isolated test document\n')
        before = {w['hwnd'] for w in native.list_visible_windows()}
        subprocess.Popen(['notepad.exe', str(scratch.resolve())])
        window = new_window(before, lambda w: scratch.stem in w['title'])
        owned.append(window)
        frame = session.begin(window_id=window['hwnd'], purpose='Edit the isolated scratch document')

        def act(kind, **params):
            nonlocal frame
            result = session.act(_confirmed=True, frame_id=frame['frame_id'], kind=kind, **params)
            if not result['ok']: raise RuntimeError(str(result))
            frame = result['post_observation']
            if not frame['ok']: raise RuntimeError(str(frame))
            return frame

        act('hotkey', keys=['ctrl', 'a'])
        act('type', text='Wingent native input verified')
        act('hotkey', keys=['ctrl', 's'])
        actual = scratch.read_text(encoding='utf-8-sig')
        assert actual.rstrip('\r\n') == 'Wingent native input verified', repr(actual)
        print(json.dumps({'application': 'Notepad', 'passed': True, 'oracle': 'saved scratch file read-back (terminal newline allowed)'}), flush=True)

        before = {w['hwnd'] for w in native.list_visible_windows()}
        subprocess.Popen(['calc.exe'])
        window = new_window(before, lambda w: 'calculator' in w['title'].lower())
        owned.append(window)
        frame = session.begin(window_id=window['hwnd'], purpose='Compute in the newly opened calculator')
        for keys in [['escape'], ['7'], ['multiply'], ['8'], ['enter']]:
            act('hotkey', keys=keys)
        names = [c['name'] for c in frame['controls']]
        passed = any('56' in name for name in names)
        print(json.dumps({'application': 'Calculator', 'passed': passed, 'display_matches': [n for n in names if '56' in n]}), flush=True)
        if not passed: raise RuntimeError('Calculator did not expose the expected result')
    finally:
        session.close_task('native-smoke')
        execution_task_id.reset(token)
        api = native.user32()
        api.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        for window in owned:
            current = next((w for w in native.list_visible_windows() if w['hwnd'] == window['hwnd'] and w['pid'] == window['pid']), None)
            if current: api.PostMessageW(window['hwnd'], 0x10, 0, 0)


if __name__ == '__main__':
    run()
