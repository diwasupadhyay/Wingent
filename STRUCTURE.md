# Structure

## Desktop runtime additions
- `backend/app/task_state.py`: generic task/action/observation/evidence models, execution budgets, compact working context.
- `backend/app/runtime.py`: application-independent observation-driven execution and verification state machine.
- `backend/app/launch_runtime.py`: production registry adapter, initial-plan compatibility, bounded provider, launch-only observation boundary.
- `backend/tests/test_runtime.py`: controlled-adapter tests for adaptive actions, verification, failure recovery, cancellation, and budgets.
- `backend/tests/test_launch_runtime.py`: production-adapter and API integration regression tests.
- `backend/app/planner.py`: strict bounded plans and semantic action compilation.
- `backend/app/executor.py`: runtime compatibility entry point and disconnect-aware planning wait.
- `backend/app/folders.py`: known-folder and explicit local directory resolution.
- `scripts/evaluate-planner.py`: opt-in live Ollama regression corpus; no tool execution.
- `backend/app/applications.py` resolves approved Chrome and Edge executables for direct browser launches.
- `backend/sidecar.py` is the frozen-backend entry point used by the Windows package.
- `scripts/build-backend-sidecar.ps1` produces the target-triple-named PyInstaller binary.
- `src-tauri/src/lib.rs` owns the overlay, tray, backend child process, shortcut, and Ollama controls.
- `backend/app/routing.py` contains conservative deterministic command parsing and action classification.
- `backend/app/model_routing.py` selects the configured local model tier for text-only requests.

## Root
- `src/` — Vite React application shell and polished command bar UI.
- `backend/` — FastAPI backend, local model provider integration, and API tests.
- `src-tauri/` — Tauri v2 Windows shell and native global shortcut integration.
- `scripts/` — development helpers for local startup.
- `docs/` — project architecture, security, setup, and status documents.

## Responsibilities
- `src/App.tsx` — command bar UX, retry/cancellation state, stream parsing, and web fallback shortcut handling.
- `backend/app/main.py` — persistent service entry point, deterministic routing, disconnect-aware SSE command API.
- `backend/app/llm.py` — Ollama provider wrapper.
- `backend/app/models.py` — validated request/response schemas.
- `backend/app/tools.py` — deterministic support tools with permission classifications.
