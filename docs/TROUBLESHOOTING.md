# Troubleshooting

## Ollama/model unavailable

Check `http://127.0.0.1:11434/api/tags`. Start installed Ollama through Wingent or normally. The configured model must appear in the catalogue; the vision path needs a vision-capable model. Current default: `qwen3-vl:4b-instruct`. A running server alone is not model readiness.

## Wrong backend or stale EXE

Rebuild Python sidecar, then Tauri EXE. Packaged Wingent owns a private per-run port and verifies runtime plus instance ID; port 8000 belongs only to browser-development defaults. Never kill an unrelated listener to make a health check pass. Keep the backend binary beside the release EXE.

## App opens but input fails

Windows may deny foreground focus; Wingent should pause rather than type elsewhere. Bring the intended app forward and resume. A closed/replaced window needs a fresh observation/grant. Avoid simultaneous manual input during tests.

Legacy `desktop_*` actions in a new trace indicate an old runtime/tool catalogue: production v24 uses only `computer_*` GUI tools.

## Result not verified

This is not equivalent to no action. Review the recorded effects and visible app. Model finish or an input acknowledgement cannot independently certify arbitrary goals. Do not retry the entire task if effects may already have occurred.

## Python imports

Run from repository root with `pytest.ini`; for direct scripts set `$env:PYTHONPATH='backend'`.

## Cancellation

Use Stop in the overlay (Ctrl+Space opens it). Holding Escape during native dispatch also stops further input; a brief tap during model reasoning is not a global latched stop. Cancellation cannot undo earlier effects.
