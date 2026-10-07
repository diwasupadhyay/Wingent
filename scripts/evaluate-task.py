"""Run a real desktop goal through the same brain used by the EXE.

$env:PYTHONPATH='backend'; python scripts/evaluate-task.py --goal 'Open Calculator and calculate 72 * 2' --calculator-result 144
"""
import argparse
import asyncio
import json
import subprocess

from app.approvals import ApprovalStore
from app.llm import OllamaClient
from app.self_operating import run_self_operating


async def run(args):
    async def connected(): return False
    terminal = None
    async for event, payload in run_self_operating(args.goal, OllamaClient(), connected,
            ApprovalStore(), max_rounds=16, seconds=420):
        print(json.dumps({'event': event, **payload}), flush=True)
        if event in {'final', 'error', 'clarification'}:
            terminal = (event, payload)
        if event == 'confirmation_required':
            raise RuntimeError('Manual approval needed; use Wingent for this task.')
    passed = bool(terminal and terminal[0] == 'final' and terminal[1].get('outcome') == 'completed')
    if args.calculator_result:
        # Independent test oracle, never exposed as an app-specific agent tool.
        script = '''Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$root = [System.Windows.Automation.AutomationElement]::RootElement
$condition = [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty, 'Calculator')
$window = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $condition)
if ($null -eq $window) { throw 'Calculator window not found' }
$displayCondition = [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::AutomationIdProperty, 'CalculatorResults')
$display = $window.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $displayCondition)
if ($null -eq $display) { throw 'Calculator display not found' }
$display.Current.Name'''
        result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', script],
            capture_output=True, text=True, timeout=15, creationflags=0x08000000)
        display = result.stdout.strip()
        import re
        numbers = re.findall(r'-?[\d,]+(?:\.\d+)?', display)
        oracle = result.returncode == 0 and numbers and numbers[-1].replace(',', '') == args.calculator_result
        print(json.dumps({'calculator_display': display, 'oracle_passed': bool(oracle)}), flush=True)
        passed = passed and oracle
    if not passed:
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--goal', required=True)
    parser.add_argument('--calculator-result')
    asyncio.run(run(parser.parse_args()))
