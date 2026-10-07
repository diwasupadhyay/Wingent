import runpy
from pathlib import Path


def test_fixture_oracle_parses_compact_and_spaced_json():
    script = Path(__file__).resolve().parents[2] / 'scripts' / 'evaluate-computer.py'
    applied = runpy.run_path(str(script))['fixture_applied']
    assert applied('{"applied":"Hello from Wingent"}')
    assert applied('PowerShell startup\n{"applied": "Hello from Wingent"}\n')
    assert not applied('{"applied":"Different text"}')
