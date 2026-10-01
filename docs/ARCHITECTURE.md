# Architecture

## Packaged desktop lifecycle
- The borderless overlay stays out of the taskbar and lives in the system tray.
- Closing hides the overlay; quitting is explicit through the tray.
- The package starts a frozen FastAPI sidecar. Tray Quit terminates the owned PyInstaller process tree.
- Native health checks require Wingent's `/health` response, so an unrelated service on port 8000 is not mistaken for the backend.
- Native Ollama checks use loopback port 11434; Start Ollama can only invoke ollama serve.

The project separates the command UI from the local reasoning service to keep the interface fast and the model/provider logic replaceable.

## Frontend
- Vite + React + TypeScript command bar.
- Keyboard-first UX with Ctrl+Space toggling and Enter-to-run behavior.
- HTTP streaming from the backend to show planning, tool progress, and partial model output.
- AbortController cancellation, Escape-to-cancel, and retry of the last failed request.

## Backend
- FastAPI service runs locally and exposes a command endpoint and health endpoint.
- The service validates prompts, checks local Ollama availability, and streams progress/status deltas back to the UI.
- Deterministic safe tools run only when the whole command is supported. Unsupported action requests return an explicit error before any tool executes.
- The registry enforces safe, confirmation-required, and restricted permissions.
- The optional `OLLAMA_COMPLEX_MODEL` tier handles long or analysis-style text prompts; other text prompts use `OLLAMA_MODEL`.
- Client disconnects stop the stream so cancellation does not leave a model request running unnecessarily.

## Desktop shell
- Tauri v2 hosts the frontend as a Windows desktop app.
- The native global Ctrl+Space shortcut shows, focuses, or hides the command bar.
- Closing the window hides it so the background app remains available; tray and startup controls are planned follow-up work.

## Local LLM provider
- `OllamaClient` implements a simple provider abstraction.
- Future provider interfaces can plug into the same API without reshaping the UI.

## Design trade-offs
- This version prioritizes a short round-trip, minimal complexity, and safety by keeping model calls local and explicit.
- Browser automation, desktop automation, and voice support are intentionally deferred to later milestones.
