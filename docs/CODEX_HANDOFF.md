# Wingent Codex Handoff

## Active implementation plan

The user authorized the goal-driven agent roadmap on 2026-10-01. Read [AGENT_IMPLEMENTATION_PLAN.md](AGENT_IMPLEMENTATION_PLAN.md) first for phase status, current evidence, unresolved decisions, and the next exact work slice. Phases 0 and 1 are verified complete; Phase 2 is next. The runtime is application-independent, but current real adapters still only launch safe targets and cannot verify page/window contents. Broader capabilities described there are planned, not implemented; older scope notes below describe the launcher baseline.

Latest checks: 82 backend tests, 9 UI tests, 7 live planner evaluations, sidecar/release builds, and packaged two-tab command. Both EXE and sidecar were rebuilt; `/health` exposes `runtime: observation-loop-v1`. Rebuild both artifacts after future code phases so the user can test the actual update.

## October 2026 update
- Natural tasks now use structured local LLM planning with strict tool validation, full-plan preflight, cancellation, a 60-second planning deadline, and per-step SSE results.
- Verified the user's YouTube GenAI search + GitHub tab request against local llama3.2:3b. `scripts/evaluate-planner.py` dry-runs seven language cases without launching anything.
- Folder opening supports Windows known folders and explicit existing local paths. Unknown project folders require a full path; no file reading, modification, or executable launching.
- The overlay shows steps and clarifications; partial execution never offers a whole-task retry. Clarifications currently require resubmitting the full request (no conversational memory).
- The UI is now a minimal, transparent launcher overlay that expands only for status or output.
- The native window is borderless, always on top, hidden from the taskbar, and resident in the system tray.
- The tray provides Open and Quit; left-click and Ctrl+Space both toggle the overlay.
- Ollama has a native readiness indicator and constrained start action.
- Packaged builds include and automatically manage a PyInstaller FastAPI sidecar.
- The next milestone is explicit confirmation request/response UI, followed by optional launch-at-login.
- Deterministic actions execute only when every command step is supported; unsupported requests do not partly launch apps or sites.
- `OLLAMA_COMPLEX_MODEL` optionally routes longer and analysis-style text requests to another installed local model.

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
- The native Tauri shortcut controls the desktop overlay.

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

Browser launch plus navigation becomes one URL action with an explicit browser parameter. Chrome/Edge executables are resolved from installation paths or PATH and launched directly with arguments. Search, search-for, look-up, seach, and serach are supported. GitHub and YouTube support site search after navigation.

Profile selection is intentionally unsupported. A request such as `Open Chrome and select any profile and open YouTube` returns an explicit browser-automation limitation instead of partially launching Chrome and getting stuck at the profile selector.

## Desktop Shell

`src-tauri/src/lib.rs` provides:

- Native `Ctrl+Space` global shortcut
- Show/focus/hide behavior for the main window
- Close-to-hide behavior so closing the window does not exit the background app
- Tauri logging in debug builds

Optional launch-at-login remains follow-up work.

## Verification

- Packaged release rebuilt and launched after the planner change. Its live SSE endpoint accepted the exact YouTube GenAI + GitHub Chrome plan (two steps), opened Downloads, and clarified "open chrome and something else" without executing tools. This verifies launch acceptance, not rendered browser contents.
- Seven live llama3.2:3b planning evaluations passed via `scripts/evaluate-planner.py`.
- Backend suite: 57 tests passing at the latest check; frontend suite: 6 tests passing.
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

1. Extend the natural-language evaluation corpus and add short-lived clarification context (currently users resubmit a complete request).
2. Add a managed browser session with observed navigation/page results before claiming page interaction or research capabilities. Decide explicitly whether to use a separate agent profile; do not take over private browser sessions implicitly.
3. Add explicit confirmation request/response before any consequential tools, and then optional launch-at-login.

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
