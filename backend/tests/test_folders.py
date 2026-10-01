import pytest

from app.folders import resolve_folder
from app.tools import ToolRegistry
from app.routing import detect_deterministic_tools


def test_folder_open_is_directory_only(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr('app.tools.os.startfile', lambda *args: calls.append(args), raising=False)
    result = ToolRegistry().execute('open_folder', {'path': str(tmp_path)})
    assert result['path'] == str(tmp_path.resolve())
    assert calls == [(str(tmp_path.resolve()), 'explore')]


def test_file_cannot_be_launched_as_folder(tmp_path):
    file = tmp_path / 'script.cmd'
    file.touch()
    with pytest.raises(ValueError, match='not a folder'):
        resolve_folder(str(file))


@pytest.mark.parametrize('path', ['relative/path', r'\\server\share', 'shell:startup'])
def test_rejects_unsafe_folder_targets(path):
    with pytest.raises(ValueError):
        resolve_folder(path)


def test_registry_rejects_model_permission_and_extra_arguments():
    with pytest.raises(ValueError, match='Unexpected'):
        ToolRegistry().validate('open_url', {'url': 'https://github.com', 'confirmed': True})


def test_known_and_exact_folders_use_fast_path():
    assert detect_deterministic_tools('open my downloads folder') == [('open_folder', {'path': 'downloads'})]
    assert detect_deterministic_tools('open "D:\\My Projects"') == [('open_folder', {'path': 'D:\\My Projects'})]
