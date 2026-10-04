# Wingent Architecture

## General computer update (2026-10-04)

`AgentBrain` receives goal/history/schemas and the latest approved window image in one local multimodal call. It proposes; the runtime validates, approves and dispatches. `ComputerSession` owns task/window grants and one-use frames; `windows_computer.py` supplies Win32 SendInput, bounded capture and UI Automation through fixed workers, with no application workflow logic. Post-action images feed the next decision.

Structured APIs remain preferred. Unfamiliar apps can use accessibility or screenshot coordinates. Input acceptance is not goal success. Window grants are broad UI authority, not a complete semantic sandbox. Native cross-app input has live evidence; general autonomous reliability remains open. Older component limitations below describe the v16 baseline where superseded.

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
| operator.py / working_context.py | Select tools, retain model planning notes and a host action index, retrieve omitted task results, check file coverage and bound repeated observations | Live planning/stopping is not proven across varied tasks; model notes can be stale |
| runtime.py / task_state.py | Generic state machine, budgets, outcomes, fresh evidence gate and clarification history | Arbitrary natural-language goals lack independent verifiers |
| tools.py / capabilities.py | Typed tool contracts, permissions, metadata, guidance | Built-in launchers retain narrow compatibility behavior |
| approvals.py | Expiring task/action/revision-bound single-use approvals | Not a security boundary against a compromised local session |
| file_tools.py | Approved list/read/create primitives | No destructive mutation or adversarial filesystem sandbox |
| desktop_tools.py | Approved fresh-target Win32 child-control click/text and scoped navigation-key dispatch with bounded post-action observation | Does not see browser/canvas pixels or verify whole workflows |
| process_tools.py | Native executable discovery and approved bounded process run with task cancellation hook | Not a sandbox; detached descendants are not guaranteed to stop |
| application_tools.py | Bounded App Paths/Start menu/PATH/install-root discovery and exact-path approved launch | Native `.exe` only; launch/window effects not live verified, UWP may be missed |
| screen_tools.py | Per-action-approved, foreground-window in-memory PNG capture and local Ollama vision description | No live interactive capture verified; model text is not a reliable pixel target or goal verifier |
| browser_tools.py | Experimental isolated Chrome profile, page/link/media observation and bounded navigation/play attempt | Live CDP control did not complete in this restricted session; no playback claim |
| window_observer.py | Read-only visible top-level window/process/title and foreground-at-capture observations, plus launch visibility check | Does not establish page state, pixel content or sustained focus |
| plugins.py | Explicit trusted startup entry-point loading | No model-driven loading or arbitrary frozen host-plugin support |
| llm.py / model_routing.py | Local provider and configured model selection; actual selected-model availability, one transient readiness retry and specific failure codes | Better small-corpus results, but repeated launch and held-out reliability gates still fail |

Natural requests use the operator and generic runtime. The operator proposes the next tool and arguments together, validates them against the registered schema, and requests separate typed arguments only if needed. After each result it decides again. It loads detailed capability guidance after that capability becomes active, keeping unrelated instructions out of the first local-model context. For an explicit flexible media request, a selected, observed page with paused HTML media can trigger the registered Play tool without an extra model call; normal review/permission and post-action time-progress checks still apply. Specific-title requests do not use that shortcut. Invalid model output after earlier actions now ends with an honest partial result rather than erasing the action history behind an error. Exact supported launch shortcuts use the launch adapter; executor.py, planner.py and capability_planner.py retain compatibility/evaluation responsibilities. They do not define the desired general-agent architecture.

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

Current context preserves the original goal, clarification answers, optional model notes (outcomes, constraints, output targets, questions and remaining work), and a host index of all task records with IDs/statuses/content hashes. Recent distinct result bodies share a 12,000-character budget; clipped/older bodies can be retrieved in chunks through `task_read_result` without repeating external actions. This tool belongs to a copied per-task registry, so concurrent tasks cannot access one another's records. Retrieval is historical data, never a fresh observation. Planning notes are limited to 2400 characters, reference only existing record IDs, and cannot grant authority or verified completion. Prior outcomes/constraints remain visible when later notes omit them; mistaken interpretations still require model/user correction.

For UTF-8 source files, the host checks contiguous page coverage of the latest observed file identity/size/modification version before allowing report creation. Page gaps and version changes expose the missing offset; old pages cannot fill a new version. This is not proof against adversarial replacement or semantic report errors. Observation refresh is bounded to one explained retry unless an intervening accepted state-changing action supplies a reason to observe again.

Context survives a short-lived in-memory clarification. State is single-use, expires after 15 minutes, has a 16-task capacity and is lost on process restart; in-flight resume disconnects are not reconciled. Clarification answers now participate in target grounding, so supplied names/paths can be used on continuation. Persistent personal memory is separate and optional.

A planner proposes criteria; it cannot certify its own execution. Planned verification must distinguish semantic goal correctness, tool postconditions, artifact validity and mere action acceptance. Unverifiable goals need transparent partial/unverified reporting and bounded stopping, not indefinite execution.

## Deployment and current limits

Tauri hosts the React overlay; it starts a frozen FastAPI sidecar on a per-run loopback port and checks a per-run instance marker before sending commands. The UI obtains that port from Tauri. Browser-only development can run FastAPI separately on port 8000; Tauri development uses its own sidecar when available. Tray Quit handles the owned backend tree; closing the overlay hides it. Ollama remains a separately installed local service.

An initial Win32 child-control adapter observes selected visible windows and provides approval-gated, fresh-target click/text and single navigation-key dispatch with a bounded post-action observation. A separate approved `screen_inspect` adapter captures only a recent foreground window into memory and sends it to loopback Ollama for a bounded description; pixels are not saved or returned to the operator. It is not general Windows UI Automation, arbitrary keyboard access or verified screenshot-driven control. An approved native process adapter can discover executables and run exact argument vectors with bounded output/time; cancellation attempts to stop its owned child/tree, but detached descendants and earlier effects remain uncertain. It is not a sandbox. Arbitrary visual input does not exist yet. A limited agent-owned Chrome DOM/media adapter is present but not live-verified; personal Chrome sessions remain untouched. Plugin entry points are trusted code and must be packaged with the frozen backend. Current local approval tokens and filesystem path checks are not a universal sandbox.

Code slices must rebuild and test both backend sidecar and EXE. The current slice did so; see the plan for exact evidence and limitations.
