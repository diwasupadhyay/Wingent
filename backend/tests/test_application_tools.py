from pathlib import Path
import pytest

from app.application_tools import ApplicationSession, register
from app.tools import ToolPermission, ToolRegistry, execution_task_id


def test_exact_start_app_avoids_filesystem_scan(monkeypatch):
    from app import application_tools
    found = [{'name': 'Calculator', 'path': r'shell:AppsFolder\Package_name!App', 'source': 'Windows Start apps'}]
    monkeypatch.setattr(application_tools, 'discover_packaged', lambda _: found)
    monkeypatch.setattr(application_tools.os, 'walk', lambda *_: pytest.fail('Unnecessary install scan'))
    assert application_tools.discover_installed('Calculator') == found


def test_packaged_apps_are_bound_to_observed_start_catalogue():
    path = r'shell:AppsFolder\Microsoft.WindowsCalculator_8wekyb3d8bbwe!App'
    calls = []
    session = ApplicationSession(catalog=lambda _: [{'name': 'Calculator', 'path': path, 'source': 'Windows Start apps'}],
                                 launcher=lambda target: (calls.append(target), 123)[1])
    token = execution_task_id.set('packaged-test')
    try:
        item = session.search('Calculator')['applications'][0]
        assert session.prepare_open({'discovery_id': item['discovery_id']})['path'] == path
        assert session.open(item['discovery_id'], path)['ok']
        assert not session.open(item['discovery_id'], path)['ok']
        assert calls == [path]
    finally:
        execution_task_id.reset(token)


def test_legacy_notepad_launch_uses_direct_process_and_reports_window(monkeypatch):
    from app import tools, window_observer
    calls = []
    class Process:
        pid = 4321
        def poll(self):
            return None
    monkeypatch.setattr(tools.subprocess, 'Popen', lambda args, **kwargs:
                        (calls.append((args, kwargs)), Process())[1])
    monkeypatch.setattr(window_observer, 'list_visible_windows', lambda: [
        {'pid': 4321, 'hwnd': 7, 'title': 'Untitled - Notepad', 'process': 'notepad.exe'}])
    result = ToolRegistry._open_application({'application': 'notepad'})
    assert calls[0][0] == ['notepad.exe']
    assert calls[0][1]['shell'] is False
    assert result['pid'] == 4321
    assert result['visible_windows'][0]['window_id'] == 7


def test_discovered_app_launch_is_task_bound_and_single_use(tmp_path):
    executable = tmp_path / 'Fixture.exe'
    executable.write_bytes(b'fixture')
    calls = []
    clock = [100.0]
    session = ApplicationSession(
        catalog=lambda query: [{'name': 'Fixture', 'path': str(executable), 'source': 'App Paths'}],
        launcher=lambda path: (calls.append(path), 123)[1], clock=lambda: clock[0])
    token = execution_task_id.set('task-a')
    try:
        found = session.search('Fixture')['applications'][0]
        execution_task_id.set('task-b')
        assert session.open(found['discovery_id'], found['path'])['effect'] == 'no_effect'
        assert not calls
        execution_task_id.set('task-a')
        found = session.search('Fixture')['applications'][0]
        assert session.open(found['discovery_id'], str(tmp_path / 'Other.exe'))['effect'] == 'no_effect'
        found = session.search('Fixture')['applications'][0]
        assert session.open(found['discovery_id'], found['path'])['effect'] == 'accepted'
        assert session.open(found['discovery_id'], found['path'])['effect'] == 'no_effect'
        assert calls == [str(executable.resolve())]
    finally:
        execution_task_id.reset(token)


def test_changed_or_expired_discovery_cannot_launch(tmp_path):
    executable = tmp_path / 'Fixture.exe'
    executable.write_bytes(b'fixture')
    calls = []
    clock = [100.0]
    session = ApplicationSession(
        catalog=lambda query: [{'name': 'Fixture', 'path': str(executable), 'source': 'PATH'}],
        launcher=lambda path: calls.append(path), clock=lambda: clock[0])
    first = session.search('Fixture')['applications'][0]
    executable.unlink()
    assert session.open(first['discovery_id'], first['path'])['effect'] == 'no_effect'
    executable.write_bytes(b'fixture')
    second = session.search('Fixture')['applications'][0]
    executable.write_bytes(b'changed fixture')
    assert session.open(second['discovery_id'], second['path'])['effect'] == 'no_effect'
    third = session.search('Fixture')['applications'][0]
    clock[0] += 61
    assert session.open(third['discovery_id'], third['path'])['effect'] == 'no_effect'
    assert not calls


def test_start_menu_shortcut_target_is_discovered_without_execution(tmp_path, monkeypatch):
    from app.application_tools import discover_installed
    menu = tmp_path / 'Microsoft/Windows/Start Menu/Programs'
    menu.mkdir(parents=True)
    (menu / 'Fixture App.lnk').write_bytes(b'fixture shortcut')
    executable = tmp_path / 'Fixture.exe'
    executable.write_bytes(b'fixture')
    monkeypatch.setenv('APPDATA', str(tmp_path))
    monkeypatch.setenv('PROGRAMDATA', str(tmp_path / 'missing'))
    monkeypatch.setenv('PATH', '')
    called = []

    class Result:
        returncode = 0
        stdout = '{"name":"Fixture App","path":' + __import__('json').dumps(str(executable)) + '}'

    monkeypatch.setattr('app.application_tools.subprocess.run',
                        lambda args, **kwargs: (called.append((args, kwargs)), Result())[1])
    found = discover_installed('Fixture App')
    assert found == [{'name': 'Fixture App', 'path': str(executable.resolve()), 'source': 'Start menu'}]
    assert any('Fixture App.lnk' in kwargs.get('input', '') for _, kwargs in called)


def test_standard_install_root_finds_native_app_not_on_path(tmp_path, monkeypatch):
    from app.application_tools import discover_installed
    target = tmp_path / 'Vendor' / 'NoteSpace' / 'NoteSpace.exe'
    target.parent.mkdir(parents=True)
    target.write_bytes(b'fixture')
    monkeypatch.setenv('PROGRAMFILES', str(tmp_path))
    monkeypatch.setenv('PROGRAMFILES(X86)', str(tmp_path / 'missing'))
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'missing'))
    monkeypatch.setenv('APPDATA', str(tmp_path / 'missing'))
    monkeypatch.setenv('PROGRAMDATA', str(tmp_path / 'missing'))
    monkeypatch.setenv('PATH', '')
    found = discover_installed('NoteSpace')
    assert {'name': 'NoteSpace.exe', 'path': str(target.resolve()),
            'source': 'Install directory'} in found


def test_application_open_requires_approval(tmp_path):
    executable = tmp_path / 'Fixture.exe'
    executable.write_bytes(b'fixture')
    session = ApplicationSession(catalog=lambda query: [
        {'name': 'Fixture', 'path': str(executable), 'source': 'PATH'}], launcher=lambda path: 123)
    registry = ToolRegistry()
    register(registry, session)
    assert registry.get_tool('application_search').permission == ToolPermission.SAFE
    assert registry.get_tool('application_open').permission == ToolPermission.CONFIRMATION_REQUIRED
    found = registry.execute('application_search', {'query': 'fixture'})['applications'][0]
    import pytest
    with pytest.raises(PermissionError):
        registry.execute('application_open', {'discovery_id': found['discovery_id'], 'path': found['path']})
    with pytest.raises(ValueError, match='does not match'):
        registry.prepare('application_open', {'discovery_id': found['discovery_id'],
                                              'path': str(tmp_path / 'Wrong.exe')})
    assert registry.prepare('application_open', {'discovery_id': found['discovery_id']})['path'] == found['path']
