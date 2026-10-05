# Wingent Architecture

Updated: 2026-10-05. Existing Tauri v2 + React/TypeScript/Vite UI, Python FastAPI/SSE backend and replaceable local Ollama provider.

## Control flow

`Goal/context -> AgentBrain -> typed proposal -> policy/approval -> tool -> fresh observation -> verification/replan`

- `main.py`: API, registry and provider selection. Natural tasks enter `operator.py`; exact launch shortcuts retain a compatibility fast path.
- `operator.py` / `brain.py`: one next tool with typed arguments, bounded repair, original goal and current approved image. Optional app-specific tools are peers, not limits.
- `runtime.py` / `task_state.py`: budgets, observe/decide/validate/execute/verify transitions, cancellation and truthful accepted/no-effect/unknown outcomes.
- `working_context.py`: host action index, bounded model notes, task-local historical retrieval and file-page/version completeness.
- `tools.py` / `approvals.py`: strict schemas, permissions, preconditions, timeouts, exact-action expiring single-use approval.
- `computer_tools.py` / `windows_computer.py`: grants, screenshots/UIA and generic native input.

## One computer environment

Production exposes `computer_begin`, `computer_observe`, `computer_action`, `computer_confirm_action`. Historical `desktop_*` and `screen_inspect` adapters stay in compatibility tests, not the planner catalogue.

Default window scope binds HWND/PID/executable. Explicit desktop scope grants task-long cross-window operation. `computer_observe()` follows the foreground without stealing focus; an observed window ID switches apps within desktop scope. Each action observes again, including newly opened foreground dialogs. Capture/input still target one foreground window, not the entire virtual desktop or secure desktop.

Actions: click, type, hotkey, scroll, UIA invoke, hover, bounded wait, and exact-approved same-window drag. UIA exposes supported patterns and bounded document text. When custom/canvas controls expose only a Pane, a previous visual click can establish the input target.

Frames expire and are single-use after possible input. The host rechecks foreground, process identity, geometry and coarse pixel changes. Post-action screenshots are new evidence, not automatically proof of goal completion. Screens/UIA/tool text remain untrusted data. Known password controls stop capture.

## Other capabilities

Files provide approved listing, bounded UTF-8 reads and exclusive new artifacts with read-back. Application discovery/launch and bounded native process execution use the same contracts. Experimental browser APIs operate an isolated profile; real playback is not established by simulated-browser evaluations. Trusted skill entry points load only through explicit startup configuration; no model installation/import authority.

## Context and completion

The original goal, clarifications and host action history survive replanning. Model notes are bounded to 2400 characters and remain interpretations. Recent distinct results share a 12,000-character budget; `task_read_result` retrieves older results without external redispatch. File reports require contiguous observed pages of the same version.

Model finish stays unverified unless trusted fresh evidence covers all criteria. Tool dispatch, matching artifact bytes and semantic goal correctness are distinct. Unknown effects cannot be blindly retried.

API budgets: 12 model calls including repair, 180 seconds, 16 actions, 24 decisions, 2 recoveries. Base task defaults differ. Clarification continuation is single-use, in-memory, up to 15 minutes/16 tasks, not crash-safe.

## Packaging and UX

Tauri owns a frozen backend on a per-run private loopback port and verifies runtime plus instance identity. The React overlay retrieves that port through Tauri. Browser-only development may use port 8000. Ollama runs separately. Tray Quit stops the owned backend tree; overlay close hides the window.

Approval hides the overlay for input handoff. Stop revokes the grant; holding Escape during native dispatch also stops further input. It cannot undo prior effects. The UI distinguishes approvals, partial effects and unverified completion.

## Remaining limits

No universal semantic verifier, durable restart recovery, guaranteed detached-descendant cleanup, elevated/secure desktop, or proven arbitrary-app competence. Capture can include occluding content and sensitive custom controls may not advertise password roles. See [security](SECURITY.md), [plan](AGENT_IMPLEMENTATION_PLAN.md) and [reference review](evaluations/SELF_OPERATING_REFERENCES.md).
