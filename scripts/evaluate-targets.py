"""Independent native coordinate check, not a model-reasoning benchmark.

Run: $env:PYTHONPATH='backend'; python scripts/evaluate-targets.py
Uses only its own temporary window. Does not change display scaling.
"""
import json
import queue
import threading
import tkinter as tk

from vendor.self_operating_computer.operate.utils.operating_system import OperatingSystem


def run():
    root = tk.Tk()
    root.title('Wingent Target Calibration')
    root.geometry('720x420+160+120')
    hits = []
    buttons = []
    for index in range(20):
        # Duplicate labels test geometry, not first-text-match selection.
        button = tk.Button(root, text='Target', command=lambda i=index: hits.append(i))
        button.grid(row=index // 5, column=index % 5, sticky='nsew', padx=8, pady=8)
        buttons.append(button)
    for row in range(4):
        root.rowconfigure(row, weight=1)
    for column in range(5):
        root.columnconfigure(column, weight=1)
    root.update()
    root.lift()
    root.focus_force()
    centers = [(b.winfo_rootx() + b.winfo_width() // 2,
                b.winfo_rooty() + b.winfo_height() // 2) for b in buttons]
    stopped = threading.Event()
    results = queue.Queue()
    passed = False

    def work():
        desktop = OperatingSystem(stopped)
        try:
            observations = []
            for scope in ('screen', 'window'):
                desktop.observe(scope)
                desktop.screenshot()
                if desktop.context()['active_window'] != 'Wingent Target Calibration':
                    raise RuntimeError('Calibration window is not foreground; no input sent for this scope.')
                left, top, right, bottom = desktop.capture_bounds
                observations.append({'scope': scope, 'bounds': desktop.capture_bounds,
                                     'screen_size': desktop.capture_screen_size})
                for x, y in centers:
                    desktop.mouse({'x': (x-left)/(right-left-1), 'y': (y-top)/(bottom-top-1)})
                desktop.wait(.1)
            results.put({'observations': observations})
        except Exception as exc:
            results.put({'error': str(exc) or type(exc).__name__,
                         'captured_window': desktop.capture_window,
                         'current_window': desktop.window_state()})

    def poll():
        nonlocal passed
        try:
            result = results.get_nowait()
        except queue.Empty:
            root.after(100, poll)
            return
        passed = 'error' not in result and hits == list(range(20)) * 2
        print(json.dumps({**result, 'oracle_passed': passed, 'hits': hits,
                          'expected_hits': 40, 'model_used': False}), flush=True)
        root.destroy()

    root.protocol('WM_DELETE_WINDOW', stopped.set)
    root.after(500, lambda: threading.Thread(target=work, daemon=True).start())
    root.after(600, poll)
    root.mainloop()
    if not passed:
        raise SystemExit(1)


if __name__ == '__main__':
    run()
