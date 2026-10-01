# Structure

## Desktop runtime additions
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
