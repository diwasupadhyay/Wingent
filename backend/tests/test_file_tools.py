import pytest

from app.file_tools import register
from app.tools import ToolRegistry


def approved(registry, name, params):
    args = registry.prepare(name, params)
    tool = registry.get_tool(name)
    item = registry.approvals.request('test', name, tool.revision, args)
    registry.approvals.respond(item.id, item.token, True)
    return registry.execute(name, params, task_id='test', approval_id=item.id)


def test_real_file_discovery_read_create_and_no_overwrite(tmp_path):
    registry = ToolRegistry()
    register(registry)
    source = tmp_path / 'source.txt'
    source.write_text('measured input', encoding='utf-8')
    listing = approved(registry, 'list_directory', {'path': str(tmp_path)})
    assert listing['entries'][0]['path'] == str(source)
    result = approved(registry, 'read_text', {'path': str(source)})
    assert result['text'] == 'measured input'
    destination = tmp_path / 'report.md'
    created = approved(registry, 'create_text', {'path': str(destination), 'text': result['text']})
    assert created['content_matches'] is True
    again = approved(registry, 'create_text', {'path': str(destination), 'text': 'replacement'})
    assert again['effect'] == 'no_effect'
    assert destination.read_text() == 'measured input'


def test_file_access_requires_exact_approval(tmp_path):
    registry = ToolRegistry()
    register(registry)
    with pytest.raises(PermissionError):
        registry.execute('list_directory', {'path': str(tmp_path)})
    for path in ['relative.txt', r'\\server\share\file', str(tmp_path / 'NUL.txt')]:
        with pytest.raises(ValueError):
            registry.prepare('read_text', {'path': path})


def test_utf8_page_boundary(tmp_path, monkeypatch):
    registry = ToolRegistry()
    register(registry)
    source = tmp_path / 'utf8.txt'
    source.write_text('abc\u20acdef', encoding='utf-8')
    monkeypatch.setattr('app.file_tools.PAGE_BYTES', 5)
    first = approved(registry, 'read_text', {'path': str(source)})
    assert first['text'] == 'abc' and first['next_offset'] == 3
    monkeypatch.setattr('app.file_tools.PAGE_BYTES', 2048)
    second = approved(registry, 'read_text', {'path': str(source), 'offset': 3})
    assert second['text'] == '\u20acdef'


def test_binary_file_rejected(tmp_path):
    registry = ToolRegistry()
    register(registry)
    source = tmp_path / 'binary'
    source.write_bytes(b'\x00binary')
    assert approved(registry, 'read_text', {'path': str(source)})['effect'] == 'no_effect'


def test_missing_read_is_known_no_effect(tmp_path):
    registry = ToolRegistry()
    register(registry)
    result = approved(registry, 'read_text', {'path': str(tmp_path / 'missing.txt')})
    assert not result['ok'] and result['effect'] == 'no_effect'
