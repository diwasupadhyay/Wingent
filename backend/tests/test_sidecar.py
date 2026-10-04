import runpy

import pytest
import uvicorn


def test_sidecar_uses_port_supplied_by_desktop_shell(monkeypatch):
    calls = []
    monkeypatch.setenv('WINGENT_BACKEND_PORT', '54321')
    monkeypatch.setattr(uvicorn, 'run', lambda app, **kwargs: calls.append(kwargs))
    runpy.run_module('sidecar', run_name='__main__')
    assert calls == [{'host': '127.0.0.1', 'port': 54321, 'log_level': 'warning'}]


def test_sidecar_rejects_invalid_port(monkeypatch):
    monkeypatch.setenv('WINGENT_BACKEND_PORT', '0')
    with pytest.raises(ValueError, match='valid TCP port'):
        runpy.run_module('sidecar', run_name='__main__')
