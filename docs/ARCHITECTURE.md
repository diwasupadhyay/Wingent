# Wingent Architecture

Updated: 2026-10-03. This document separates current implementation from proposed design. Phase status and execution authorization belong to [AGENT_IMPLEMENTATION_PLAN.md](AGENT_IMPLEMENTATION_PLAN.md).

## Product and boundaries

Wingent is a local-first general computer operator with a minimal command overlay. A task describes an outcome, not a named automation. Applications and workflow examples do not appear in the core runtime's decision structure.

Intended loop: goal → understand → plan → observe → select capability → validate/approve → act → observe → verify → replan. Prefer reliable structured mechanisms; fallbacks retain the same host-enforced policies.

## Implemented components

| Owner | Responsibility | Present limitation |
| --- | --- | --- |
| src/App.tsx | Command input, SSE states, actions, approvals, cancellation, clarification answer and unverified output | Resume is only for explicit questions; no durable conversation |
| src-tauri/src/lib.rs | Overlay/tray/shortcut, packaged sidecar ownership, Ollama controls, required backend-runtime check | Browser/lifecycle hardening remains; incompatible port occupant is refused, not killed |
| main.py / task_store.py | Local command API, registry setup, provider selection and bounded in-memory clarification continuation | State is lost on restart or interrupted resume |
| operator.py | Discover registered tools, select next tool, generate typed arguments, retain distinct results and bound repeat correction | Live planning/stopping is not proven across varied tasks |
| runtime.py / task_state.py | Generic state machine, budgets, outcomes, fresh evidence gate and clarification history | Arbitrary natural-language goals lack independent verifiers |
| tools.py / capabilities.py | Typed tool contracts, permissions, metadata, guidance | Built-in launchers retain narrow compatibility behavior |
| approvals.py | Expiring task/action/revision-bound single-use approvals | Not a security boundary against a compromised local session |
| file_tools.py | Approved list/read/create primitives | No destructive mutation or adversarial filesystem sandbox |
| desktop_tools.py | Approved fresh-target Win32 child-control click/text and scoped navigation-key dispatch with bounded post-action observation | Does not see browser/canvas pixels or verify whole workflows |
| process_tools.py | Native executable discovery and approved bounded process run with task cancellation hook | Not a sandbox; detached descendants are not guaranteed to stop |
| application_tools.py | Bounded App Paths/Start menu/PATH/install-root discovery and exact-path approved launch | Native `.exe` only; launch/window effects not live verified, UWP may be missed |
| browser_tools.py | Experimental isolated Chrome profile, page/link/media observation and bounded navigation/play attempt | Live CDP control did not complete in this restricted session; no playback claim |
| window_observer.py | Read-only visible top-level window/process/title and foreground-at-capture observations, plus launch visibility check | Does not establish page state, pixel content or sustained focus |
| plugins.py | Explicit trusted startup entry-point loading | No model-driven loading or arbitrary frozen host-plugin support |
| llm.py / model_routing.py | Local provider abstraction and configured model selection | Current model/configuration fails live reliability gate |

Natural requests use the operator and generic runtime. Exact supported launch shortcuts use the launch adapter; executor.py, planner.py and capability_planner.py retain compatibility/evaluation responsibilities. They do not define the desired general-agent architecture.

API tasks currently use 180 seconds, 12 model calls including argument generation/repair, 16 actions, 24 decisions and 2 recoveries. Base TaskState defaults remain 120 seconds / 6 model calls; the API overrides them. Per-operation and per-tool limits also apply. Document limits accurately; do not raise them to hide loops.

## Tool and evidence contracts

A registered tool defines input/output schemas, description, capability, permission, revision, timeout, cancellation and retry semantics, with optional precondition, observer and verifier hooks.

The model proposes actions. The host validates targets and permissions, obtains any required exact-action approval, reobserves/revalidates, then dispatches. Skill guidance or external content cannot grant authority.

Outcomes distinguish accepted, known no effect and unknown. Dispatch acknowledgement is not verified completion. Current creation tools compare written bytes with the proposed content; that proves artifact consistency, not factual accuracy or satisfaction of the original goal. A model finish stays unverified unless trusted fresh evidence covers every criterion.

Slow reasoning triggers observation refresh. Changed facts require replanning; unchanged facts still require validation before dispatch. Cancellation stops scheduling new work but cannot undo already dispatched synchronous effects. Unknown effects must not be blindly replayed.

## Intended architecture (not fully implemented)

1. Goal/context layer: original intent, constraints, outcomes, unresolved questions, compact durable evidence references and remaining work.
2. Reasoning layer: bounded planning, capability selection, failure diagnosis and replanning; model/provider choices remain replaceable.
3. Capability discovery layer: availability, dependencies, schemas and relevant trusted guidance; no global prompt full of every installed skill.
4. Policy layer: scoped grants, action approvals, revocation, target identity and external-content distrust.
5. Execution adapters: Windows/accessibility, browser DOM, application APIs, files, controlled processes, screenshot/input.
6. Evidence layer: fresh observations, capability-owned postconditions, artifact/source checks and explicit unverifiable results.
7. Continuity layer: clarification/resume, checkpoints and reconciliation of interrupted/unknown effects.
8. Evaluation/diagnostics: separate contract, adapter, model and packaged evidence; concise progress without secrets or private reasoning traces.

These layers extend the existing code incrementally. They are not a request to replace the project or scaffold all components at once.

## Adapter selection and generality

Discover what is actually installed and permitted. Prefer a structured API or accessibility target over blind input; use controlled executable tools when appropriate; use vision/input only with explicit scope and fresh targets when structured tools cannot do the job.

No app-specific milestone may change the core runtime. Domain knowledge can live in optional capabilities. Missing functionality should produce a precise limitation or required decision, not a fabricated success or automatic plugin installation.

## Working context and completion

Current context is bounded and retained through a short-lived in-memory clarification. Completed action records are preserved, and the model sees recent distinct results plus clarification answers. State is single-use, expires after 15 minutes, has a 16-task capacity and is lost on process restart; in-flight resume disconnects are not reconciled. Persistent personal memory is separate and optional.

A planner proposes criteria; it cannot certify its own execution. Planned verification must distinguish semantic goal correctness, tool postconditions, artifact validity and mere action acceptance. Unverifiable goals need transparent partial/unverified reporting and bounded stopping, not indefinite execution.

## Deployment and current limits

Tauri hosts the React overlay; the packaged app owns a frozen FastAPI sidecar on loopback. Development starts the backend separately. Tray Quit handles the owned backend tree; closing the overlay hides it. Ollama remains a separately installed local service.

An initial Win32 child-control adapter observes selected visible windows and provides approval-gated, fresh-target click/text and single navigation-key dispatch with a bounded post-action observation. It is not general Windows UI Automation, arbitrary keyboard access or screenshot/vision understanding. An approved native process adapter can discover executables and run exact argument vectors with bounded output/time; cancellation attempts to stop its owned child/tree, but detached descendants and earlier effects remain uncertain. It is not a sandbox. Arbitrary visual input does not exist yet. A limited agent-owned Chrome DOM/media adapter is present but not live-verified; personal Chrome sessions remain untouched. Plugin entry points are trusted code and must be packaged with the frozen backend. Current local approval tokens and filesystem path checks are not a universal sandbox.

Code slices must rebuild and test both backend sidecar and EXE. The current slice did so; see the plan for exact evidence and limitations.
