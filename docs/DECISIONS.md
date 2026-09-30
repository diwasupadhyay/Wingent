# Decisions

## Launcher overlay
Wingent uses a fixed-width, borderless, always-on-top surface that stays out of the taskbar. It expands only for useful progress or output and uses explicit tray Quit semantics.

## Frozen backend sidecar
The Windows package includes a PyInstaller-built FastAPI binary named for the Rust target triple. Tauri launches it only when port 8000 is free and owns the spawned process, removing the end-user Python requirement.

## Local-first model default
We default to Ollama to avoid network dependencies and keep the app local-first.

## Streaming before full chat history
The first version streams partial outputs to the UI for a faster perceived response and better cancellation UX.

## Minimal but structured state
The app keeps a clear status and message lifecycle instead of relying on loose chat history.

## No speculative automation yet
Browser automation, desktop control, and voice are intentionally deferred until the command bar and backend loop are proven.
