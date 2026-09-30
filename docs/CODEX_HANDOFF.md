# Wingent Codex Handoff

## October 2026 update
- The UI is now a minimal, transparent launcher overlay that expands only for status or output.
- The native window is borderless, always on top, hidden from the taskbar, and resident in the system tray.
- The tray provides Open and Quit; left-click and Ctrl+Space both toggle the overlay.
- Ollama has a native readiness indicator and constrained start action.
- Packaged builds include and automatically manage a PyInstaller FastAPI sidecar.
- The next milestone is explicit confirmation request/response UI, followed by optional launch-at-login.

Use this document as the starting context for future work on Wingent.

## Product Brief

Build Wingent as a fast, modern, local-first Windows desktop AI agent.

The target experience is a lightweight AI command bar, not a generic chatbot. It should open instantly with a global shortcut, accept text commands, stream useful progress, use controlled tools, recover from failures, and ask before consequential actions.

Stack:

- Tauri v2 desktop shell
- React + TypeScript + Vite frontend
- Python 3.12+ FastAPI backend with SSE streaming
- Ollama behind a replaceable local LLM provider interface
- Vitest and pytest tests

The first stable scope is M0/M1 plus the initial safe tool layer. Do not add advanced browser automation, vision, voice, semantic memory, or autonomous computer-use features unless explicitly requested later.

## Current Implementation

### Frontend

- `src/App.tsx` contains the command bar, streaming parser, progress states, cancellation, retry, Escape handling, and web fallback shortcut.
- The frontend calls `http://127.0.0.1:8000/api/command` unless `VITE_API_BASE_URL` is set.
- UI states include `planning`, `tool_running`, `streaming`, `done`, and `error`.
- The native Tauri shortcut is supplemented by the browser shortcut fallback.

### Backend

- `backend/app/main.py` exposes `/health` and `POST /api/command`.
- The command endpoint streams SSE events: `status`, `delta`, `final`, and `error`.
- Client disconnects are checked so cancelled requests stop streaming.
- CORS allows Vite origins and Tauri origins, including `http://tauri.localhost`.
- Deterministic safe actions run before the LLM path.

### Ollama

- Default URL: `http://127.0.0.1:11434`
- Default model: `llama3.2:3b`
- The model is installed and live generation was verified.
- Override with `OLLAMA_BASE_URL` and `OLLAMA_MODEL`.

### Tools and command parsing

`backend/app/tools.py` contains a permission-aware registry:

- `open_url`: safe; only HTTP and HTTPS URLs are allowed.
- `open_application`: safe; limited to Chrome, Edge, Notepad, and Explorer.
- `confirmation_required` and `restricted` are enforced by the registry even though no consequential tool is currently registered.

Supported deterministic examples:

- `open example.com`
- `open Chrome`
- `open Chrome and open https://example.com`
- `open YouTube`
- `open YouTube and search piano tutorials`

When a website is requested, the parser removes the separate Chrome launch action. This prevents two Chrome windows. YouTube searches become a single URL such as `https://www.youtube.com/results?search_query=piano+tutorials`.

Profile selection is intentionally unsupported. A request such as `Open Chrome and select any profile and open YouTube` returns an explicit browser-automation limitation instead of partially launching Chrome and getting stuck at the profile selector.

## Desktop Shell

`src-tauri/src/lib.rs` provides:

- Native `Ctrl+Space` global shortcut
- Show/focus/hide behavior for the main window
- Close-to-hide behavior so closing the window does not exit the background app
- Tauri logging in debug builds

Tray menu, startup launch, and persistent background-service management are planned follow-up work.

## Verification

- Backend suite: 12 tests passing at the latest check.
- Frontend suite: passing.
- `npm run build`: passing.
- `cargo check` in `src-tauri`: passing.
- Ollama `/api/generate`: verified with `llama3.2:3b`.
- Tauri CORS preflight from `http://tauri.localhost`: verified with HTTP 200.

The native executable was built at:

`src-tauri/target/release/app.exe`

The full `npm run tauri:build` command may exit nonzero when the optional MSI bundle cannot download WiX. That does not invalidate `app.exe` when release compilation reports it was built successfully.

## Running Locally

Start FastAPI separately:

```powershell
Set-Location 'd:\Wingent'
$env:PYTHONPATH = 'backend'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Verify it:

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/health'
```

Start the Tauri development app in another terminal:

```powershell
Set-Location 'd:\Wingent'
npm run tauri:dev
```

Ollama must be running separately with `llama3.2:3b` installed.

## Next Work, In Order

1. Make backend startup reliable for the packaged Windows app, preferably through a controlled sidecar or a clearly documented launcher without hiding errors.
2. Add an explicit confirmation request/response flow for future consequential tools; never silently auto-approve them.
3. Add a tray menu and optional startup behavior after validating the background-app lifecycle.
4. Improve command parsing only for safe, deterministic workflows that have tests.
5. Add integration tests for SSE cancellation, retry, and the packaged Tauri origin.

Do not implement profile clicking, arbitrary browser control, DOM automation, voice, vision, semantic memory, or autonomous desktop control as an unrequested shortcut.

## Ready-to-Use Codex Prompt

You are continuing work on the Wingent repository at `d:\Wingent`.

Build and maintain Wingent as a fast, modern, local-first Windows desktop AI agent. The main experience is a lightweight command bar, not a generic chatbot. Use Tauri v2 with React, TypeScript, and Vite for the desktop shell; Python 3.12+ with FastAPI and SSE for the persistent local backend; and Ollama behind a replaceable provider interface. The installed local model is `llama3.2:3b`.

Read `docs/CODEX_HANDOFF.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, and `MEMORY.md` before editing. Preserve existing user changes. Prefer small, tested changes. Before editing, identify the owning code path, state one falsifiable hypothesis, and name the cheapest check that could disconfirm it. After every substantive edit, run the narrowest relevant test immediately.

Requirements:

- global `Ctrl+Space` command-bar activation on Windows
- text command input
- local Ollama reasoning with streamed output
- visible planning, tool, streaming, completion, cancellation, retry, and error states
- deterministic safe tools before model fallback
- permission enforcement and confirmation gates for consequential tools
- no secrets, no network LLM dependency, and no speculative autonomous behavior
- ask before consequential actions

The current safe tools are approved application launches and HTTP/HTTPS URL launches. YouTube can be opened directly and deterministic YouTube search URLs are supported. Browser profile selection is intentionally unsupported and must remain explicit rather than pretending it succeeded. Do not add advanced browser automation, voice, vision, memory, or autonomous computer-use features unless the user explicitly changes scope.

When running the project, start FastAPI separately on `127.0.0.1:8000`, ensure Ollama is available, and run the Tauri frontend in another terminal. Validate with backend pytest, frontend Vitest/build, and `cargo check` as relevant. Do not commit or create branches unless explicitly asked.
