import json
import subprocess
from types import SimpleNamespace
from app.accessibility import read_targets


def test_observer_has_timeout_and_no_input_commands(monkeypatch):
    calls = []
    def run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0, stdout=json.dumps([{'name': 'Button', 'rect': [1, 2, 3, 4]}]))
    monkeypatch.setattr(subprocess, 'run', run)
    assert read_targets(123)[0]['name'] == 'Button'
    assert calls[0][1]['timeout'] == 3
    assert 'FromHandle([IntPtr]123)' in calls[0][0][-1]


def test_observer_timeout_is_optional_not_task_failure(monkeypatch):
    def run(*args, **kwargs):
        raise subprocess.TimeoutExpired('powershell', 3)
    monkeypatch.setattr(subprocess, 'run', run)
    assert read_targets(123) == []
