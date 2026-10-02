from types import SimpleNamespace

import pytest

from app.capabilities import Arguments
from app.plugins import load_skills
from app.tools import ToolRegistry, ToolPermission


def test_only_explicitly_enabled_skill_is_loaded(monkeypatch):
    registry = ToolRegistry()
    calls = []
    def register(target):
        calls.append(True)
        target.register('custom_probe', 'New tool', ToolPermission.SAFE, {}, lambda _: {'ok': True}, input_model=Arguments)
    monkeypatch.setattr('app.plugins.entry_points', lambda **_: [SimpleNamespace(name='probe', load=lambda: register)])
    assert load_skills(registry) == [] and calls == []
    assert load_skills(registry, ['probe']) == ['probe']
    assert registry.execute('custom_probe')['ok']


def test_plugin_cannot_replace_registered_tool(monkeypatch):
    registry = ToolRegistry()
    original = registry.get_tool('open_url')
    def bad(target):
        target.tools.pop('open_url')
    monkeypatch.setattr('app.plugins.entry_points', lambda **_: [SimpleNamespace(name='bad', load=lambda: bad)])
    with pytest.raises(ValueError):
        load_skills(registry, ['bad'])
    assert registry.get_tool('open_url') is original
