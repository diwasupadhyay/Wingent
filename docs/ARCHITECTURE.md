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

### Phase 1 runtime

- `task_state.py` defines application-independent tasks, criteria, actions, observations, outcomes, evidence, and budgets. No Chrome/Excel names occur in the core contracts or runtime.
- `runtime.py` runs observe/decide/validate/execute/observe/verify transitions through injected planner, observer, executor, and verifier interfaces. Only trusted verifier evidence for every criterion from the latest fresh observation can complete a task.
- `launch_runtime.py` connects the actual existing registry to this loop. Its observations check tool prerequisites, not windows or pages. Its verifier deliberately supplies no desktop evidence: successful launches terminate as **unverified**, not completed.
- Simple launch sequences remain deterministic between checks. A changed prerequisite can trigger bounded local-model replanning before dispatch; after dispatched/unknown effects, the adapter asks for intervention rather than substituting apps or replaying earlier actions.
- Default task limits: 120 seconds total (including initial planning), 60 seconds per async operation, 16 action records, 24 decisions, 6 model generations (including repair), and 2 recoveries. Action target evidence expires after 5 seconds and is refreshed before dispatch.
- Working state is request-local: four recent observations retained, two bounded observations and six bounded recent action records sent to a planner. There is no persistent personal memory or cross-request resume yet.
- OS launch calls run off the event loop. Cancellation stops scheduling further actions but cannot forcibly terminate an already-dispatched OS call; that result is unknown and cannot be blindly retried.
- Current seed planner still uses the bounded launch vocabulary. Registry-driven capability discovery and approval lifecycle are Phase 2; actual window/browser/Excel observation adapters are later phases. Generic recovery/verification is tested with controlled adapters, not claimed as live desktop capability.

- Exact safe commands use the deterministic fast path. Natural/ambiguous requests go to a bounded structured Ollama planner (`planner.py`), which returns execute, clarify, or answer.
- Search targets are encoded by code, not used as shell strings. The compiler removes redundant browser/home-page launches immediately before navigation/search.
- `executor.py` retains the compatibility entry point and disconnect-aware planning wait; the launch adapter preflights the whole initial plan, then the runtime revalidates each action immediately before dispatch.
- Planning has a 60-second total deadline and at most one schema-repair attempt. Disconnect cancels the pending model request. Maximum plan size is eight steps.
- Folder opening resolves Windows known folders or explicit existing local directories. No file content is read and executable files cannot be launched as folders.
- Launch acceptance is the only observation currently available. Browser page contents, profile selection, and rendered tabs are not observed/verified.

- FastAPI service runs locally and exposes a command endpoint and health endpoint.
- The service validates prompts, checks local Ollama availability, and streams progress/status deltas back to the UI.
- Deterministic safe tools run only when the whole command parses. The planner is instructed to clarify unsupported or ambiguous requests without actions; model intent interpretation is not a correctness guarantee.
- The registry enforces safe, confirmation-required, and restricted permissions.
- The optional `OLLAMA_COMPLEX_MODEL` tier handles long or analysis-style text prompts; other text prompts use `OLLAMA_MODEL`.
- Client disconnects stop the stream so cancellation does not leave a model request running unnecessarily.

## Desktop shell
- Tauri v2 hosts the frontend as a Windows desktop app.
- The native global Ctrl+Space shortcut shows, focuses, or hides the command bar.
- Closing hides the window. The tray provides Open/Quit; launch-at-login is deferred.

## Local LLM provider
- `OllamaClient` implements a simple provider abstraction.
- Future provider interfaces can plug into the same API without reshaping the UI.

## Design trade-offs
- This version prioritizes a short round-trip, minimal complexity, and safety by keeping model calls local and explicit.
- Browser automation, desktop automation, and voice support are intentionally deferred to later milestones.
