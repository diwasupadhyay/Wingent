# Architecture

## Current direction — 2026-10-02

Wingent is a general computer operator, not an application-specific agent. The current production natural-task path is `main.py → operator.py → AgentRuntime → typed registry`. `operator.py` chooses a tool from the actual installed registry, generates typed arguments, and feeds actual outcomes into the next decision. The old full-plan planner is retained for compatibility/evaluations, not used for natural-task execution.

General built-in file primitives live in `file_tools.py`; `plugins.py` loads explicitly enabled installed `wingent.skills` entry points. Skills are trusted native code, not model-provided executable instructions. Extensions supply schemas, permissions, prerequisites, timeouts, observation and verification hooks through the existing registry. Do not add app names or workflow branches to the runtime. Registry guidance can teach tool usage but cannot authorize actions.

The current API budget is 12 model calls and 180 seconds. Selected-tool argument generation consumes the same budget. Exact simple launch requests retain the model-free path. Files require exact action approval; reads are paged, directory listing is nonrecursive, and creation is exclusive with read-back. Goal verification is intentionally separate from these artifact checks. No implicit global desktop observation exists yet.

Roadmap layers are reasoning/discovery, structured computer adapters, controlled process/code execution, vision/input fallback, then task continuity/hardening. Windows APIs, browser DOM, application APIs and future computer input are interchangeable capability providers, not separate products. See the active tracker; legacy sections below describe prior implementation stages.

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

### Phase 2 capabilities and approvals

- `capabilities.py` defines strict input/output models and trusted, permission-neutral domain guidance. Excel/research are explicitly unavailable; guidance never registers a tool or grants permission.
- `capability_planner.py` generates a Pydantic plan union from the actual registered tools and their typed arguments. Restricted tools are excluded. New typed tools need no changes to the planner's action enum. `planner.py` remains only for legacy plan compatibility/tests.
- Tool definitions include input/output schemas, permission, capability, timeout, cancellation semantics, retry safety, precondition normalization, optional observation and verification hooks, and a revision identity. Rich new tools must supply a Pydantic input model; the legacy schema adapter supports simple string fields only.
- Preparation validates without granting authority. Execution revalidates canonical arguments and consumes an approval when required; the old `confirmed=True` bypass no longer exists.
- `approvals.py` stores random, expiring, single-use requests bound to task ID, tool, tool revision, and canonical arguments. Tokens are delivered only through the task stream, never to the model. Denial, expiry, cancellation, replacement, changed arguments, and replay cannot authorize dispatch.
- Runtime waits for the explicit response, then refreshes observations and revalidates before dispatch. Approval waits count toward task/operation deadlines. Pending approvals are revoked when the stream ends.
- The overlay's optional Review toggle applies the same approval flow even to safe launches. No destructive/consequential OS tool was added just to demonstrate approval.
- `/api/capabilities` exposes available typed tools/domain knowledge; `/health` marker is `capabilities-v2`.
- Structured generation uses an 8192-token context window. Live evaluation caught schema-valid but incomplete plans; prompt/context fixes and an explicit-domain omission guard are tested. This guard is conservative and is not general proof of semantic completeness.

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
