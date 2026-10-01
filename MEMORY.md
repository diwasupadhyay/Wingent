# Memory

## October 2026 desktop update
- Browser commands support generic search/search-for/look-up and common search typos. Explicit Chrome/Edge selection is retained through URL execution.
- "Open Chrome and search GitHub" opens a web search in Chrome; "open GitHub and search tauri" searches GitHub itself.
- Wingent now uses a borderless, taskbar-free launcher overlay that expands only for progress and results.
- A system tray icon provides Open and Quit; left-click toggles the overlay.
- Packaged builds start and own a PyInstaller FastAPI sidecar when port 8000 is free.
- The command bar shows native Ollama status and can run the constrained ollama serve action.
- Deterministic routing now executes only when every requested step is supported; mixed tasks fail without side effects.
- Text-only requests route to the configured local model, with an optional complex model tier.
- Tray Quit now stops the owned PyInstaller process tree so the backend does not remain running after normal exit.
- Native backend readiness verifies Wingent's health response, and the overlay shows a compact service error when it is unavailable.
- Optional launch-at-login, voice, vision, semantic memory, and autonomous computer use remain deferred.

## Current status
- Repository initialized as a local-first Windows AI command bar project.
- The workspace is intentionally minimal: a Vite + React + TypeScript frontend, a Python FastAPI backend, and an Ollama-backed local LLM provider interface.
- M1 is complete: the command bar is live, persistent, streaming, and connected to a local backend.
- M2 is complete for deterministic safe app and URL launches, with enforced permission-aware execution.
- The Tauri shell is active with a native Ctrl+Space shortcut and close-to-hide behavior.
- The desktop UI is a borderless, taskbar-free launcher overlay that expands only for progress and results.
- A system tray icon provides Open and Quit actions; left-click toggles the overlay.
- The packaged app starts and owns a PyInstaller FastAPI sidecar when port 8000 is not already in use.
- Ollama status is shown in the command bar and a constrained native action can start ollama serve.

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
- Startup launch, voice, vision, semantic memory, and autonomous computer-use remain deferred.
