"""Discover native Windows applications and launch only fresh, task-owned results.

App Paths, Start menu, PATH and standard install roots are bounded discovery sources.
Launching an approved executable is still a consequential action, not a sandbox.
"""

import os
import json
import re
import subprocess
import threading
import time
from pathlib import Path
from uuid import uuid4

from pydantic import Field

from app.capabilities import Arguments, Capability
from app.tools import ToolPermission, execution_task_id


class SearchApplications(Arguments):
    query: str = Field(min_length=2, max_length=80)


class OpenDiscoveredApplication(Arguments):
    discovery_id: str = Field(min_length=32, max_length=32, pattern=r'^[0-9a-f]{32}$')
    path: str | None = Field(default=None, min_length=1, max_length=2048)


def _native_path(value):
    path = Path(value)
    if not path.is_absolute() or str(path).startswith(('\\', '//')) or path.suffix.casefold() != '.exe':
        return None
    try:
        if not path.is_file() or path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
            return None
        return path.resolve(strict=True)
    except OSError:
        return None


def discover_installed(query):
    """Search registered App Paths, Start menu shortcuts and executables on PATH."""
    needle = query.casefold().strip()
    terms = [term for term in re.findall(r'[a-z0-9]{3,}', needle)
             if term not in {'app', 'application', 'installed', 'native'}]
    if len(needle) < 2:
        return []
    candidates = []
    if os.name == 'nt':
        import winreg
        key_name = r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths'
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for view in (0, winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY):
                try:
                    with winreg.OpenKey(hive, key_name, 0, winreg.KEY_READ | view) as root:
                        count = winreg.QueryInfoKey(root)[0]
                        for index in range(min(count, 4000)):
                            name = winreg.EnumKey(root, index)
                            if needle not in name.casefold():
                                continue
                            try:
                                with winreg.OpenKey(root, name) as entry:
                                    value, _ = winreg.QueryValueEx(entry, '')
                                candidates.append((name, os.path.expandvars(value), 'App Paths'))
                            except (OSError, TypeError):
                                continue
                except OSError:
                    continue
        shortcut_paths = []
        for variable in ('APPDATA', 'PROGRAMDATA'):
            root = os.environ.get(variable)
            if not root:
                continue
            start_menu = Path(root) / 'Microsoft/Windows/Start Menu/Programs'
            if not start_menu.is_dir():
                continue
            visited = 0
            for folder, dirs, files in os.walk(start_menu):
                visited += 1
                if visited > 1000 or len(shortcut_paths) >= 40:
                    dirs.clear()
                    break
                for name in files:
                    if name.casefold().endswith('.lnk') and needle in name.casefold():
                        shortcut_paths.append(str(Path(folder) / name))
                        if len(shortcut_paths) >= 40:
                            break
        if shortcut_paths:
            # Fixed read-only script; shortcut paths arrive as JSON on stdin,
            # never as executable PowerShell code.
            script = ("$paths = [Console]::In.ReadToEnd() | ConvertFrom-Json; "
                      "$shell = New-Object -ComObject WScript.Shell; "
                      "$items = @($paths | ForEach-Object { "
                      "$s = $shell.CreateShortcut($_); "
                      "[pscustomobject]@{name=[IO.Path]::GetFileNameWithoutExtension($_); path=$s.TargetPath} "
                      "}); $items | ConvertTo-Json -Compress")
            try:
                completed = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive',
                                            '-Command', script], input=json.dumps(shortcut_paths),
                                           text=True, capture_output=True, timeout=8, check=False)
                if completed.returncode == 0 and completed.stdout.strip():
                    items = json.loads(completed.stdout)
                    for item in items if isinstance(items, list) else [items]:
                        if isinstance(item, dict) and isinstance(item.get('path'), str):
                            candidates.append((item.get('name', ''), item['path'], 'Start menu'))
            except (OSError, subprocess.TimeoutExpired, ValueError):
                pass
    # PATH discovery remains bounded and does not recurse into installed directories.
    for folder in os.environ.get('PATH', '').split(os.pathsep)[:80]:
        if not folder or not Path(folder).is_dir():
            continue
        try:
            for entry in list(Path(folder).iterdir())[:500]:
                if entry.suffix.casefold() == '.exe' and needle in entry.stem.casefold():
                    candidates.append((entry.name, str(entry), 'PATH'))
        except OSError:
            continue
    if os.name == 'nt':
        install_roots = [Path(os.environ[key]) for key in ('PROGRAMFILES', 'PROGRAMFILES(X86)')
                         if os.environ.get(key)]
        if os.environ.get('LOCALAPPDATA'):
            install_roots.append(Path(os.environ['LOCALAPPDATA']) / 'Programs')
        for root in install_roots:
            if not root.is_dir():
                continue
            visited = 0
            for folder, dirs, files in os.walk(root):
                visited += 1
                depth = len(Path(folder).relative_to(root).parts)
                if depth >= 3:
                    dirs.clear()
                if visited > 1800:
                    break
                for name in files[:500]:
                    if any(part in name.casefold() for part in ('unins', 'updater', 'elevation',
                                                                'crashpad', 'feedback', 'setup')):
                        continue
                    if name.casefold().endswith('.exe') and terms and \
                            terms[-1] in (folder + '/' + name).casefold():
                        candidates.append((name, str(Path(folder) / name), 'Install directory'))
                        if len(candidates) >= 200:
                            break
                if len(candidates) >= 200:
                    break
    candidates.sort(key=lambda item: (
        bool(terms and item[0].casefold().removesuffix('.exe') == terms[-1]),
        bool(terms and terms[-1] in item[0].casefold()),
        sum(term in (item[0] + '/' + item[1]).casefold() for term in terms),
        item[0].casefold().removesuffix('.exe') == needle,
        item[2] == 'App Paths'), reverse=True)
    found = []
    seen = set()
    for name, value, source in candidates:
        target = _native_path(value)
        if target is None or str(target).casefold() in seen:
            continue
        seen.add(str(target).casefold())
        found.append({'name': name, 'path': str(target), 'source': source})
        if len(found) >= 20:
            break
    return found


class ApplicationSession:
    def __init__(self, catalog=discover_installed, launcher=None, clock=time.monotonic):
        self.catalog = catalog
        self.launcher = launcher or self._launch
        self.clock = clock
        self.lock = threading.Lock()
        self.records = {}

    @staticmethod
    def _launch(path):
        process = subprocess.Popen([path], cwd=str(Path(path).parent), shell=False,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
        return process.pid

    def search(self, query):
        task_id = execution_task_id.get()
        results = []
        with self.lock:
            self.records = {key: value for key, value in self.records.items()
                            if self.clock() - value['at'] < 60}
            for item in self.catalog(query):
                target = _native_path(item['path'])
                if target is None:
                    continue
                discovery_id = uuid4().hex
                stat = target.stat()
                self.records[discovery_id] = {'path': str(target), 'name': item['name'],
                                              'task_id': task_id, 'at': self.clock(),
                                              'identity': (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)}
                results.append({'discovery_id': discovery_id, 'name': item['name'],
                                'path': str(target), 'source': item['source']})
                if len(results) >= 20:
                    break
        return {'ok': True, 'applications': results, 'truncated': len(results) >= 20,
                'observation': 'Searched App Paths, Start menu shortcuts, PATH and bounded standard install roots; UWP and other locations may be absent.'}

    def open(self, discovery_id, path):
        with self.lock:
            item = self.records.pop(discovery_id, None)
        if item is None or item['task_id'] != execution_task_id.get() or self.clock() - item['at'] > 60:
            return {'ok': False, 'effect': 'no_effect', 'reason': 'Discovery is missing, expired or belongs to another task.'}
        if path.casefold() != item['path'].casefold():
            return {'ok': False, 'effect': 'no_effect', 'reason': 'Requested executable does not match discovery.'}
        target = _native_path(item['path'])
        if target is None or str(target).casefold() != item['path'].casefold():
            return {'ok': False, 'effect': 'no_effect', 'reason': 'Discovered executable changed or disappeared.'}
        stat = target.stat()
        if (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns) != item['identity']:
            return {'ok': False, 'effect': 'no_effect', 'reason': 'Discovered executable changed; search again.'}
        try:
            pid = self.launcher(str(target))
        except OSError as exc:
            return {'ok': False, 'effect': 'no_effect', 'reason': f'Application did not start: {type(exc).__name__}.'}
        return {'ok': True, 'effect': 'accepted', 'application': item['name'], 'path': str(target),
                'pid': pid, 'observation': 'Process launch accepted; visible window and user goal are not verified.'}

    def prepare_open(self, params):
        with self.lock:
            item = self.records.get(params['discovery_id'])
        if item is None or self.clock() - item['at'] > 60:
            raise ValueError('Application discovery expired; search again.')
        if params.get('path') and params['path'].casefold() != item['path'].casefold():
            raise ValueError('Application path does not match the discovered executable.')
        target = _native_path(item['path'])
        if target is None:
            raise ValueError('Discovered executable disappeared; search again.')
        stat = target.stat()
        if (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns) != item['identity']:
            raise ValueError('Discovered executable changed; search again.')
        return {**params, 'path': item['path']}


def register(registry, session=None):
    session = session or ApplicationSession()
    registry.capabilities['applications'] = Capability(
        'applications', 'application_search finds native executables from Windows App Paths, Start menu shortcuts, PATH or standard install roots. '
        'application_open requires a fresh discovery_id; the host binds its exact discovered path into user approval. Launch acceptance does not prove '
        'the app became visible. UWP apps may not be found.')
    registry.register('application_search', 'Search installed native apps by name in App Paths, Start menu, PATH and install roots without launching.',
                      ToolPermission.SAFE, {}, lambda p: session.search(**p),
                      input_model=SearchApplications, capability='applications', timeout_seconds=10,
                      retry_safe=True)
    registry.register('application_open', 'Launch one freshly discovered native app after exact-action approval.',
                      ToolPermission.CONFIRMATION_REQUIRED, {}, lambda p: session.open(**p),
                      input_model=OpenDiscoveredApplication, capability='applications', timeout_seconds=10,
                      precondition=session.prepare_open)
    return session
