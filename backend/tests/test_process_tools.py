import sys
from pathlib import Path

import pytest

from app.process_tools import discover, register, run, validate_run
from app.tools import ToolPermission, ToolRegistry


def test_process_tools_are_discoverable_but_execution_needs_approval():
    registry = ToolRegistry()
    register(registry)
    assert registry.get_tool('process_discover').permission == ToolPermission.SAFE
    assert registry.get_tool('process_run').permission == ToolPermission.CONFIRMATION_REQUIRED
    found = discover({'name': Path(sys.executable).name})
    assert found['ok'] and Path(found['path']).is_file()
    with pytest.raises(PermissionError):
        registry.execute('process_run', {'executable': sys.executable, 'args': ['-c', 'print(1)'],
                                         'cwd': str(Path.cwd())})


def test_process_run_is_bounded_and_reports_exit_not_goal_success():
    result = run({'executable': sys.executable, 'args': ['-c', 'print(123)'],
                  'cwd': str(Path.cwd())})
    assert result['ok'] and result['exit_code'] == 0
    assert result['stdout'].strip() == '123'
    assert 'not independently verify' in result['observation']


def test_process_approval_is_bound_to_exact_arguments():
    registry = ToolRegistry()
    register(registry)
    parameters = {'executable': sys.executable, 'args': ['-c', 'print(123)'],
                  'cwd': str(Path.cwd())}
    canonical = registry.prepare('process_run', parameters)
    tool = registry.get_tool('process_run')
    approval = registry.approvals.request('task', tool.name, tool.revision, canonical)
    registry.approvals.respond(approval.id, approval.token, True)
    changed = {**parameters, 'args': ['-c', 'print(456)']}
    with pytest.raises(PermissionError):
        registry.execute('process_run', changed, approval_id=approval.id, task_id='task')


def test_process_run_rejects_missing_target_and_nul():
    with pytest.raises(ValueError):
        validate_run({'executable': 'missing.exe', 'args': [], 'cwd': str(Path.cwd())})
    with pytest.raises(ValueError):
        validate_run({'executable': sys.executable, 'args': ['bad\x00arg'],
                      'cwd': str(Path.cwd())})


def test_timeout_is_unknown_even_when_tree_is_stopped():
    result = run({'executable': sys.executable,
                  'args': ['-c', 'import time; time.sleep(3)'],
                  'cwd': str(Path.cwd())}, timeout_seconds=0.1)
    assert result['effect'] == 'unknown'
