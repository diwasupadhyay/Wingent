"""Opt-in interactive Windows smoke. Only controls windows launched by this run.

Run with PYTHONPATH=backend. Not an unattended CI test: requires the interactive
desktop. Creates an isolated Tk editor and native Calculator; never touches
pre-existing windows. --model asks the real local vision model for one action.
"""
import argparse
import asyncio
import json
import subprocess
import sys
import time
import tkinter as tk
from pathlib import Path

from app import windows_computer as native
from app.computer_tools import ComputerSession
from app.tools import execution_task_id


def fixture():
    root = tk.Tk()
    root.title('Wingent isolated computer evaluation')
    root.geometry('720x400+100+100')
    tk.Label(root, text='Enter a short greeting in the box below', font=('Arial', 20)).pack(pady=20)
    entry = tk.Entry(root, font=('Arial', 22), name='greeting')
    entry.pack(padx=40, fill='x')
    status = tk.Label(root, text='Waiting', font=('Arial', 18))
    status.pack(pady=20)
    def apply():
        status.config(text=entry.get())
        print(json.dumps({'applied': entry.get()}), flush=True)
    tk.Button(root, text='Apply greeting', command=apply, font=('Arial', 18)).pack()
    root.mainloop()


def run(model=False, autonomous=False):
    before = {w['hwnd'] for w in native.list_visible_windows()}
    child = subprocess.Popen([sys.executable, __file__, '--fixture'], stdout=subprocess.PIPE, text=True)
    session = ComputerSession()
    token = execution_task_id.set('interactive-smoke')
    try:
        deadline = time.monotonic() + 15
        window = None
        while time.monotonic() < deadline:
            window = next((w for w in native.list_visible_windows() if w['pid'] == child.pid and w['hwnd'] not in before), None)
            if window: break
            time.sleep(.2)
        if not window: raise RuntimeError('Isolated test window did not appear')
        if autonomous:
            from app.capabilities import Arguments
            from app.computer_tools import register
            from app.llm import OllamaClient
            from app.launch_runtime import BudgetedProvider
            from app.operator import run_operator
            from app.task_state import TaskState, Limits
            from app.tools import ToolRegistry, ToolPermission
            registry = ToolRegistry()
            registry.tools.clear()
            register(registry, session)
            registry.register('observe_windows', 'List available windows', ToolPermission.SAFE, {},
                              lambda _: {'ok': True, 'windows': [{'window_id': window['hwnd'], 'title': window['title']}]}, input_model=Arguments)
            state = TaskState(goal='In the Wingent isolated computer evaluation app, enter Hello from Wingent in the greeting box and apply the greeting. Verify the displayed result.',
                              criteria=['Greeting applied'], limits=Limits(model_calls=12, seconds=360.0))
            async def disconnected(): return False
            async def execute():
                async for event, data in run_operator(registry, state, BudgetedProvider(OllamaClient(), state), disconnected):
                    if event == 'confirmation_required':
                        if data['tool'] != 'computer_begin' or data['arguments']['window_id'] != window['hwnd']:
                            registry.approvals.respond(data['approval_id'], data['token'], False)
                        else:
                            registry.approvals.respond(data['approval_id'], data['token'], True)
                    if event in {'action', 'step', 'final', 'error', 'clarification'}:
                        print(json.dumps({'event': event, **data}), flush=True)
                    if event == 'step' and data.get('state') in {'accepted', 'failed', 'unknown'} and state.records:
                        record = state.records[-1]
                        print(json.dumps({'arguments': record.action.arguments, 'reason': record.outcome.data.get('reason')}), flush=True)
            started = time.monotonic()
            asyncio.run(execute())
            child.terminate()
            output, _ = child.communicate(timeout=5)
            passed = '"applied": "Hello from Wingent"' in output
            print(json.dumps({'oracle_passed': passed, 'seconds': round(time.monotonic()-started, 2), 'model_calls': state.model_calls,
                              'records': [{'tool': r.action.tool, 'status': r.outcome.status, 'summary': r.outcome.summary} for r in state.records]}), flush=True)
            if not passed: raise RuntimeError('Independent fixture state did not match the goal')
            return
        observed = session.begin(window_id=window['hwnd'], purpose='Evaluate isolated test application')
        Path('.build/computer-before.png').write_bytes(session.visual_context('interactive-smoke')['image'])
        print(json.dumps({'stage': 'captured', 'size': observed['image_size'], 'controls': observed['controls']}), flush=True)
        if model:
            from app.brain import AgentBrain
            from app.llm import OllamaClient
            from types import SimpleNamespace
            brain = AgentBrain(OllamaClient(), SimpleNamespace(computer_session=session), SimpleNamespace(id='interactive-smoke'))
            schema = {'type': 'object', 'properties': {'x': {'type': 'integer'}, 'y': {'type': 'integer'}}, 'required': ['x','y']}
            raw = asyncio.run(brain.structured(json.dumps({'goal': 'Locate the center of the empty greeting input box. Return normalized coordinates 0 to 1000.'}), 'Inspect the attached screenshot. Return only the requested coordinates.', schema))
            point = json.loads(raw)
        else:
            point = {'x': 500, 'y': 320}
        result = session.act(frame_id=observed['frame_id'], kind='click', **point)
        print(json.dumps({'stage': 'click', 'point': point, 'ok': result['ok'], 'reason': result.get('reason')}), flush=True)
        if not result['ok']: raise RuntimeError(str(result))
        result = session.act(frame_id=result['post_observation']['frame_id'], kind='type', text='Hello from Wingent')
        Path('.build/computer-after.png').write_bytes(session.visual_context('interactive-smoke')['image'])
        print(json.dumps({'stage': 'type', 'ok': result['ok'], 'observation': result['post_observation']}), flush=True)
        # Read only this owned fixture's pixels; model is an assessor, not independent verification.
        if model:
            schema = {'type':'object','properties':{'visible_text':{'type':'string'}},'required':['visible_text']}
            print(asyncio.run(brain.structured('{}', 'Read the text inside the greeting input box from the latest screenshot.', schema)), flush=True)
    finally:
        session.close_task('interactive-smoke')
        execution_task_id.reset(token)
        child.terminate()
        child.wait(timeout=5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixture', action='store_true')
    parser.add_argument('--model', action='store_true')
    parser.add_argument('--autonomous', action='store_true')
    args = parser.parse_args()
    fixture() if args.fixture else run(args.model, args.autonomous)
