"""Opt-in interactive Windows smoke. Only controls windows launched by this run.

Run with PYTHONPATH=backend. Not an unattended CI test: requires the interactive
desktop. Creates an isolated WinForms editor; never touches
pre-existing windows. --model asks the real local vision model for one action.
"""
import argparse
import asyncio
import json
import subprocess
import time
from pathlib import Path

from app import windows_computer as native
from app.computer_tools import ComputerSession
from app.tools import execution_task_id


FIXTURE = r'''
Add-Type -AssemblyName System.Windows.Forms
$form = New-Object System.Windows.Forms.Form
$form.Text = 'Wingent isolated computer evaluation'
$form.Size = New-Object System.Drawing.Size(720,400)
$form.StartPosition = 'Manual'
$form.Location = New-Object System.Drawing.Point(100,100)
$label = New-Object System.Windows.Forms.Label
$label.Text = 'Enter a short greeting in the box below'
$label.Location = New-Object System.Drawing.Point(40,30)
$label.Size = New-Object System.Drawing.Size(630,40)
$form.Controls.Add($label)
$entry = New-Object System.Windows.Forms.TextBox
$entry.Location = New-Object System.Drawing.Point(40,100)
$entry.Size = New-Object System.Drawing.Size(620,40)
$entry.Font = New-Object System.Drawing.Font('Arial',18)
$form.Controls.Add($entry)
$status = New-Object System.Windows.Forms.Label
$status.Text = 'Waiting'
$status.Location = New-Object System.Drawing.Point(40,180)
$status.Size = New-Object System.Drawing.Size(620,40)
$form.Controls.Add($status)
$button = New-Object System.Windows.Forms.Button
$button.Text = 'Apply greeting'
$button.Location = New-Object System.Drawing.Point(40,260)
$button.Size = New-Object System.Drawing.Size(190,45)
$button.Add_Click({
    $status.Text = $entry.Text
    [Console]::Out.WriteLine((ConvertTo-Json -Compress @{applied=$entry.Text}))
    [Console]::Out.Flush()
})
$form.Controls.Add($button)
[void]$form.ShowDialog()
'''


def fixture_applied(output):
    """Inspect fixture events as JSON, independent of PowerShell spacing."""
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get('applied') == 'Hello from Wingent':
            return True
    return False


def run(model=False, autonomous=False):
    if native.foreground_window_id() is None and not native.list_visible_windows():
        raise RuntimeError('No interactive Windows desktop is visible to this process; run this smoke test from the signed-in desktop session.')
    before = {w['hwnd'] for w in native.list_visible_windows()}
    child = subprocess.Popen(['powershell.exe', '-NoProfile', '-STA', '-Command', FIXTURE],
                             stdout=subprocess.PIPE, text=True, creationflags=0x08000000)
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
            from app.tools import ToolPermission
            from app.main import registry as production_registry
            import copy
            registry = copy.copy(production_registry)
            registry.tools = production_registry.tools.copy()
            registry.capabilities = production_registry.capabilities.copy()
            register(registry, session)
            registry.register('observe_windows', 'List available windows', ToolPermission.SAFE, {},
                              lambda _: {'ok': True, 'windows': [{'window_id': window['hwnd'], 'title': window['title']}]}, input_model=Arguments)
            state = TaskState(goal='In the Wingent isolated computer evaluation app, enter Hello from Wingent in the greeting box and apply the greeting. Verify the displayed result.',
                              criteria=['Greeting applied'], limits=Limits(model_calls=12, seconds=360.0))
            async def disconnected(): return False
            terminal = None
            async def execute():
                nonlocal terminal
                async for event, data in run_operator(registry, state, BudgetedProvider(OllamaClient(), state), disconnected):
                    if event in {'final', 'error', 'clarification'}:
                        terminal = {'event': event, 'outcome': data.get('outcome')}
                    if event == 'confirmation_required':
                        if (data['tool'] != 'computer_begin' or data['arguments']['window_id'] != window['hwnd']
                                or data['arguments'].get('scope', 'window') != 'window'):
                            registry.approvals.respond(data['approval_id'], data['token'], False)
                        else:
                            registry.approvals.respond(data['approval_id'], data['token'], True)
                    if event in {'action', 'step', 'final', 'error', 'clarification'}:
                        # Never print captured controls/screens or full provider
                        # payloads: a Windows Search pane can contain private data.
                        summary = {key: data[key] for key in ('index', 'label', 'state', 'outcome')
                                   if key in data}
                        if event in {'final', 'error', 'clarification'}:
                            summary['message'] = str(data.get('message') or data.get('text') or '')[:500]
                        print(json.dumps({'event': event, **summary}), flush=True)
                    if event == 'step' and data.get('state') in {'accepted', 'failed', 'unknown'} and state.records:
                        record = state.records[-1]
                        print(json.dumps({'arguments': record.action.arguments, 'reason': record.outcome.data.get('reason')}), flush=True)
            started = time.monotonic()
            asyncio.run(execute())
            child.terminate()
            output, _ = child.communicate(timeout=5)
            passed = fixture_applied(output)
            clean_stop = terminal is not None and terminal['event'] == 'final'
            print(json.dumps({'oracle_passed': passed, 'seconds': round(time.monotonic()-started, 2), 'model_calls': state.model_calls,
                              'clean_stop': clean_stop, 'terminal': terminal,
                              'records': [{'tool': r.action.tool, 'status': r.outcome.status, 'summary': r.outcome.summary} for r in state.records]}), flush=True)
            if not passed: raise RuntimeError('Independent fixture state did not match the goal')
            if not clean_stop: raise RuntimeError('Fixture effect succeeded, but the agent did not terminate cleanly')
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
    parser.add_argument('--model', action='store_true')
    parser.add_argument('--autonomous', action='store_true')
    args = parser.parse_args()
    run(args.model, args.autonomous)
