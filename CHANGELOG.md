# Changelog

## Unreleased
- Add bounded structured local LLM planning for natural multi-step commands, including site-specific searches and separate browser tabs.
- Add safe existing-folder opening, full-plan validation, per-step progress, explicit clarification, and partial-execution reporting.
- Prevent complex YouTube/new-tab instructions from becoming one Google query.
- Cancel pending planner calls on disconnect; limit format repair and planning duration; suppress dangerous whole-task retries after partial execution.
- Add a no-side-effect live planner evaluation script and regression tests for plans, folders, cancellation, failures and UI streaming.
- Fix "open Chrome and seach GitHub": generic searches and common typos now work, and the requested browser is retained.
- Add GitHub navigation/site search, preserve conjunctions in queries, and clarify missing or unsupported actions.
- Require all steps of a deterministic command to be supported before executing any tool.
- Add safe web search routing and an optional local complex-model tier.
- Show explicit errors for empty or failed model streams and keep cancelled requests isolated.
- Limit frontend test discovery to `src/` so inaccessible backend caches do not break Vitest.
- Stop the owned PyInstaller process tree on normal app exit, and report rejected browser launches.
- Verify the backend health response and show its unavailable state in the overlay.
- Replaced the full application window with a minimal adaptive command overlay.
- Added taskbar-free tray operation with Open, toggle, and explicit Quit behavior.
- Added native Ollama health indication and a constrained Start Ollama action.
- Added reproducible FastAPI sidecar packaging and automatic backend startup.
- Initialized Git and captured the pre-redesign baseline.

## Initial implementation
- Initialized the project for a local-first Windows AI command bar.
- Added the Vite React TypeScript frontend and FastAPI backend.
- Added a local Ollama provider interface and streaming response flow.
- Added project docs, configuration, and environment templates.
