# Architecture

The project separates the command UI from the local reasoning service to keep the interface fast and the model/provider logic replaceable.

## Frontend
- Vite + React + TypeScript command bar.
- Keyboard-first UX with Ctrl+Space toggling and Enter-to-run behavior.
- HTTP streaming from the backend to show planning, tool progress, and partial model output.
- AbortController cancellation, Escape-to-cancel, and retry of the last failed request.

## Backend
- FastAPI service runs locally and exposes a command endpoint and health endpoint.
- The service validates prompts, checks local Ollama availability, and streams progress/status deltas back to the UI.
- Deterministic safe tools run before the model path; the registry enforces safe, confirmation-required, and restricted permissions.
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
