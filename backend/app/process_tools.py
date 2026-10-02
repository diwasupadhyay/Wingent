"""Approved, bounded native process execution. An approval is not a sandbox."""

import os
import re
import shutil
import signal
import subprocess
import threading
from pathlib import Path

from pydantic import Field

from app.capabilities import Arguments, Capability
from app.tools import ToolPermission


class DiscoverExecutable(Arguments):
    name: str = Field(min_length=1, max_length=80, pattern=r'^[A-Za-z0-9_.-]+$')


class RunProcess(Arguments):
    executable: str = Field(min_length=1, max_length=2048)
    args: list[str] = Field(default_factory=list, max_length=24)
    cwd: str = Field(min_length=1, max_length=2048)


def _local_existing_path(value: str, *, directory: bool) -> Path:
    path = Path(value)
    if not path.is_absolute() or str(path).startswith(('\\', '//')):
        raise ValueError('Use an exact absolute local path, not a network or device path.')
    if not (path.is_dir() if directory else path.is_file()):
        raise ValueError('The requested directory or executable does not exist.')
    for item in (path, *path.parents):
        if item.is_symlink() or (hasattr(item, 'is_junction') and item.is_junction()):
            raise ValueError('Linked paths are not supported for process execution.')
    return path.resolve(strict=True)


def validate_run(params):
    executable = _local_existing_path(params['executable'], directory=False)
    cwd = _local_existing_path(params['cwd'], directory=True)
    if os.name == 'nt' and executable.suffix.casefold() not in {'.exe', '.com'}:
        raise ValueError('Run native executables only; scripts require an explicitly approved interpreter.')
    args = params['args']
    if any(not isinstance(arg, str) or '\x00' in arg or len(arg) > 1000 for arg in args):
        raise ValueError('Arguments must be bounded strings without NUL characters.')
    if sum(map(len, args)) > 4000:
        raise ValueError('Argument vector is too long.')
    return {**params, 'executable': str(executable), 'cwd': str(cwd)}


def discover(params):
    name = params['name']
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}', name):
        raise ValueError('Discover a simple executable name, not a path or command.')
    found = shutil.which(name)
    if not found:
        return {'ok': False, 'effect': 'no_effect', 'reason': 'Executable was not found on PATH.'}
    try:
        target = _local_existing_path(found, directory=False)
    except ValueError:
        return {'ok': False, 'effect': 'no_effect', 'reason': 'Executable path is unsupported.'}
    if os.name == 'nt' and target.suffix.casefold() not in {'.exe', '.com'}:
        return {'ok': False, 'effect': 'no_effect', 'reason': 'PATH entry is a script; discover its interpreter instead.'}
    return {'ok': True, 'path': str(target), 'name': name,
            'observation': 'Found on the current PATH; not executed.'}


def _bounded_reader(pipe, chunks):
    with pipe:
        while data := pipe.read(4096):
            if sum(map(len, chunks)) < 8192:
                chunks.append(data[:max(0, 8192 - sum(map(len, chunks)))])


def _stop_tree(process):
    if process.poll() is not None:
        return True
    try:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                           capture_output=True, timeout=3, check=False)
        else:
            os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=3)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return process.poll() is not None


def run(params, *, timeout_seconds=12):
    params = validate_run(params)
    # Do not pass the backend's whole environment (which may contain credentials).
    allowed = ('SystemRoot', 'WINDIR', 'PATH', 'PATHEXT', 'TEMP', 'TMP',
               'APPDATA', 'LOCALAPPDATA', 'USERPROFILE')
    environment = {key: os.environ[key] for key in allowed if key in os.environ}
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
    try:
        process = subprocess.Popen([params['executable'], *params['args']],
                                   cwd=params['cwd'], env=environment, shell=False,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, creationflags=flags,
                                   start_new_session=os.name != 'nt')
    except OSError as exc:
        return {'ok': False, 'effect': 'no_effect', 'reason': f'Process did not start: {type(exc).__name__}.'}
    stdout, stderr = [], []
    readers = [threading.Thread(target=_bounded_reader, args=(pipe, chunks), daemon=True)
               for pipe, chunks in ((process.stdout, stdout), (process.stderr, stderr))]
    for reader in readers:
        reader.start()
    try:
        code = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        stopped = _stop_tree(process)
        return {'ok': False, 'effect': 'unknown', 'reason':
                'Process timed out; its process tree was stopped as far as the host could verify. '
                'Detached children or earlier side effects may remain.' if stopped else
                'Process timed out; its process tree may still be running.', 'pid': process.pid}
    for reader in readers:
        reader.join(timeout=2)
    return {'ok': True, 'effect': 'accepted', 'exit_code': code,
            'stdout': b''.join(stdout).decode('utf-8', errors='replace')[:8192],
            'stderr': b''.join(stderr).decode('utf-8', errors='replace')[:8192],
            'output_truncated': sum(map(len, stdout)) >= 8192 or sum(map(len, stderr)) >= 8192,
            'observation': 'Parent process exited. Detached children may remain. Exit code and output do not independently verify the user goal.'}


def register(registry):
    registry.capabilities['process'] = Capability(
        'process', 'process_discover finds native executables on PATH. process_run requires an exact absolute executable, '
        'argument vector and working directory plus user approval. It has no shell and a short timeout, but is NOT '
        'a sandbox: the executable can change files, install software or access the network. Inspect targets first.')
    registry.register('process_discover', 'Find a native executable on PATH without running it.',
                      ToolPermission.SAFE, {}, discover, input_model=DiscoverExecutable,
                      capability='process', timeout_seconds=5, retry_safe=True)
    registry.register('process_run', 'Run one native executable with exact arguments and cwd after user approval; 12-second limit and bounded output.',
                      ToolPermission.CONFIRMATION_REQUIRED, {}, run, input_model=RunProcess,
                      capability='process', timeout_seconds=25, precondition=validate_run)
