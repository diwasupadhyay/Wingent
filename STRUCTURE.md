# Structure

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
