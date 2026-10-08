"""Visible, isolated fixture for the new driver; --autonomous also tests Ollama.

Run: $env:PYTHONPATH='backend'; python scripts/evaluate-computer.py [--autonomous]
Only the temporary fixture is changed; it closes itself after evaluation.
"""
import argparse
import asyncio
import json
import queue
import threading
import tkinter as tk

from app.approvals import ApprovalStore
from app.llm import OllamaClient
from app.self_operating import run_self_operating
from vendor.self_operating_computer.operate.utils.operating_system import OperatingSystem


def run(autonomous=False):
    root = tk.Tk()
    root.title('Wingent Computer Test')
    root.geometry('660x300+200+150')
    tk.Label(root, text='Wingent Computer Test', font=('Arial', 22)).pack(pady=20)
    tk.Label(root, text='Enter exactly: Wingent can see and act.').pack()
    entry = tk.Entry(root, font=('Arial', 16), width=40)
    entry.pack(pady=12)
    confirmed = tk.StringVar(value='Not submitted')
    tk.Button(root, text='Confirm', command=lambda: confirmed.set(entry.get()), takefocus=True).pack()
    tk.Label(root, textvariable=confirmed).pack(pady=10)
    root.update()
    root.lift()
    root.focus_force()
    entry.focus_set()
    x, y = entry.winfo_rootx() + 30, entry.winfo_rooty() + 15
    result = queue.Queue()
    stopped = threading.Event()
    terminal = None

    def work():
        try:
            if autonomous:
                async def connected(): return stopped.is_set()
                async def operate():
                    nonlocal terminal
                    async for event, payload in run_self_operating(
                        'In the visible Wingent Computer Test window, type Wingent can see and act. '
                        'into its text field and click Confirm. Finish when the same text appears below Confirm.',
                        OllamaClient(), connected, ApprovalStore(), max_rounds=8, seconds=240):
                        print(json.dumps({'event': event, **payload}), flush=True)
                        if event in {'final', 'error', 'clarification'}:
                            terminal = (event, payload)
                asyncio.run(operate())
            else:
                import pyautogui
                desktop = OperatingSystem(stopped)
                desktop.screenshot()
                left, top, right, bottom = desktop.capture_bounds
                desktop.mouse({'x': (x - left) / (right - left - 1), 'y': (y - top) / (bottom - top - 1)})
                desktop.write('Unicode: café')
                desktop.press(['ctrl', 'a'])
                desktop.write('Wingent can see and act.')
                desktop.press(['tab'])
                desktop.press(['space'])
                desktop.wait(0.2)
                desktop.screenshot()
            result.put(None)
        except BaseException as exc:
            result.put(str(exc) or type(exc).__name__)

    passed = False
    def poll():
        nonlocal passed
        try:
            error = result.get_nowait()
        except queue.Empty:
            root.after(100, poll)
            return
        oracle = confirmed.get() == 'Wingent can see and act.'
        clean_stop = not autonomous or bool(terminal and terminal[0] == 'final' and terminal[1].get('outcome') == 'completed')
        passed = not error and oracle and clean_stop
        print(json.dumps({'oracle_passed': passed, 'text': entry.get(),
                          'confirmed': confirmed.get(), 'error': error,
                          'effect_matched': oracle, 'clean_stop': clean_stop}), flush=True)
        root.destroy()
    root.protocol('WM_DELETE_WINDOW', lambda: stopped.set())
    root.after(800, lambda: threading.Thread(target=work, daemon=True).start())
    root.after(900, poll)
    root.mainloop()
    if not passed:
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--autonomous', action='store_true')
    run(parser.parse_args().autonomous)
