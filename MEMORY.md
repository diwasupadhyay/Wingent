# Memory

## Current status
- Repository initialized as a local-first Windows AI command bar project.
- The workspace is intentionally minimal: a Vite + React + TypeScript frontend, a Python FastAPI backend, and an Ollama-backed local LLM provider interface.
- M1 is complete: the command bar is live, persistent, streaming, and connected to a local backend.
- M2 is complete for deterministic safe app and URL launches, with enforced permission-aware execution.
- The Tauri shell is active with a native Ctrl+Space shortcut and close-to-hide behavior.

## Architectural intent
- Keep the UI and backend loosely coupled through HTTP/streaming APIs.
- Prefer deterministic, safe actions and avoid speculative complexity.
- Treat Ollama as the initial local model provider behind a clean interface for future providers.
- Keep the desktop/windowing integration intentionally lightweight until the core command loop proves useful.

## Important constraints
- Do not ship secrets or .env files.
- Do not add semantic memory or voice features before the core command bar is solid.
- Keep model/provider access local-first and explicit.
- Cancellation is client-disconnect aware, and the UI preserves failed requests for retry.
- Tray, startup, voice, vision, semantic memory, and autonomous computer-use remain deferred.
