# Wingent: Goal-Driven Agent Implementation Plan

## Direction change — 2026-10-02 (current authority)

The user explicitly changed the goal to a **general-purpose personal computer operator**. Applications and tasks below are examples, never the architecture or a fixed automation menu. This section supersedes the old application-by-application sequence retained below as historical context. Preserve useful code, not obsolete scope restrictions.

Core contract: goal → understand → observe → choose next action → validate/approve → act → observe result → verify → replan. New trusted capabilities must register without changing the core loop. Prefer structured APIs/accessibility; controlled process execution and vision are general fallback mechanisms, not shortcuts around permissions.

### Active tracker

| Phase | Capability layer | Status |
| --- | --- | --- |
| 0–1 | Baseline and generic bounded runtime | Previously verified complete |
| 2 | Typed registry and bound approvals | Verified complete: 113 backend / 12 UI tests; rebuilt EXE approval, denial and replay checks passed in preceding work |
| 3 | Production next-action reasoning, discovery, skills and general file primitives | In progress: code/tests/build and packaged safety checks pass; live-model reliability gate fails |
| 4 | Structured computer observation/control | Not complete: Windows/UI Automation, application APIs, managed browser as peer adapters; stable identities and fresh targets |
| 5 | Controlled process/code execution and tool discovery | Not implemented: exact-command approval, bounded output, process-tree lifecycle, working-directory scope, installation/configuration safeguards |
| 6 | Screenshot/vision and input fallback | Not implemented: explicit capture scope, available vision model, fresh-target checks, verified keyboard/mouse actions |
| 7 | Task continuity and reliability | Not complete: resume clarifications without replay, durable checkpoints, source/evidence tracking, mixed-capability evaluations and packaged reliability |

### Implemented in the current slice

- Natural tasks now enter `operator.py`, not the initial fixed launch planner. The real local model selects the next tool after every outcome, then generates arguments against only that tool's schema. Exact simple launch shortcuts remain optional model-free paths.
- Tool selection sees the runtime registry, capability guidance, original goal, and bounded actual results. New tools require no new action enum or phrase matching. Registered observers/verifiers remain the only authority for verified completion.
- General `list_directory`, `read_text` and `create_text` primitives support discovering unknown filenames, bounded UTF-8 reads, and new artifacts with content read-back. Every access currently requires exact-path approval; writes preview the full content and cannot overwrite an existing file.
- Explicitly enabled installed Python entry-point skills can add trusted tools at startup (`WINGENT_SKILLS`). No model-driven imports, downloads, or permission grants. This is trusted native extension code, not a plugin sandbox. Frozen distributions must bundle plugins and their metadata; loading arbitrary host Python packages into the EXE is not implemented.
- Slow inference refreshes observations and revalidates before dispatch; changed facts trigger replanning. Missing read-only resources produce known no-effect outcomes instead of falsely claiming uncertain side effects.
- API task budgets are 12 model calls / 180 seconds; tool selection and argument generation share those budgets. Unknown effects and accepted side-effect duplicates still stop safely.

### Failures observed (do not erase)

Live llama3.2:3b initially asked for redundant permission, emitted empty actions, repeated discovery, and asked the user to select a tool. A combined union decision schema was unreliable. Replaced it with separate tool selection and typed argument generation, retained host-managed approvals, and added capability-local guidance. Later testing reached real reading and caught incorrect missing-file outcome classification. These are measured limitations; passing mocked tests alone does not establish a competent general operator.

Current source verification: **123 backend tests and 12 UI tests pass**. Real local-model trials reached directory discovery → reading → exclusive report creation with matching read-back bytes, but continued redundant inspection until the model-call limit. The end-to-end evaluator correctly exits nonzero. A separate model-only progress assessor falsely claimed completion after merely listing a directory; that experiment was removed. The final implementation retains host-controlled verification and labels any model final assessment unverified. **Phase 3 is not verified complete.** Do not solve this by silently raising budgets or auto-approving actions.

Packaged testing also reproduced the failure and exposed a model-selected one-byte page size. Removed that unnecessary argument: `read_text` now uses host-controlled 2048-byte pages and the model chooses only path/offset. The subsequent source trial read complete input and created the expected 23-byte artifact but still exhausted the model-call budget after redundant inspections. This fix improves the primitive; it does not solve model planning or stopping. No terminal/vision/desktop-control success is claimed.

Next exact reasoning work: compare a user-approved alternative local model and improve goal decomposition/evidence-grounded stopping with a broader corpus. No new model was downloaded. Structured Windows observation and task continuity are also unfinished; the model issue does not imply those capabilities already exist. The test harness only approves file actions inside its temporary fixture directory, and enables Review for packaged tests so unexpected safe launch proposals cannot execute.

### Final packaged evidence — 2026-10-02

- PyInstaller sidecar, frontend production build, and `npm.cmd run tauri:build -- --no-bundle` succeeded after the last code edit.
- Launched `src-tauri/target/release/app.exe`; health reports `operator-v3`, and the live `read_text` input schema contains only path/offset (fixed page-size revision).
- Packaged denial, approval, and replay-rejection smoke tests pass. The approved action opens this repository folder; the denied URL is not launched.
- Source/packaged sidecar SHA-256 match: `1C5FEEB063136A65086F362CE507A794DE9367AA554EDFF7EBAEE05A0A412C0E`.
- Wingent and Ollama left running for user testing. No new dependency/model or third-party plugin installed; no personal documents read. Temporary test artifacts were isolated and cleaned by the test harness.
- Live operator evaluation is **not passing**. The final source revision creates the correct fixture artifact but repeats actions until budget exhaustion. Earlier packaged evaluation reproduced the same stopping defect and motivated the fixed page-size change. Do not mark Phase 3 complete or call this a finished general computer agent.

### Remaining before claiming the product complete

- [ ] Verify realistic mixed-capability goals and failure recovery with real tools and the packaged EXE.
- [ ] Independent goal-level verification, not just a file write acknowledgement or model finish message.
- [ ] General Windows/application observation, input, browser DOM, controlled terminal/code, and visual fallback.
- [ ] Continuation through clarification, scoped session read grants, plugin packaging, and long-task checkpoints.
- [ ] Broader model evaluation; request approval before downloading another model.

The earlier launcher-only restrictions are superseded by this explicit direction change. Security boundaries, action-specific approvals, honest verification, user-file protection, and finite execution budgets remain mandatory. Do not describe this slice as “can do anything on the computer.”

---

## Historical plan (superseded sequence; preserve evidence)

Created: 2026-10-01 (Asia/Calcutta)
Last updated: 2026-10-01
Status: AUTHORIZED — Phases 0 and 1 complete; Phase 2 implemented, packaged verification in progress.

## Start here

This is the living plan and progress tracker for evolving Wingent from a bounded command launcher into an observation-driven Windows agent. Read this document when resuming this work.

The user explicitly authorized starting this plan on 2026-10-01: "okay let's start with it go ahead". Work within the phased scope and existing safety rules; this is not blanket approval for consequential actions or unresolved personal-data access decisions.

- Current phase: Phase 2 packaged verification.
- Next action: verify rebuilt EXE approval/denial/replay flow, then Phase 3 Windows and file capabilities.
- Verified pre-runtime rollback checkpoint: `48acd055b8d6577a86972c4df0c42edcb943617d`.
- Current blockers: none for Phase 1. Browser-profile, model-installation, and test-data choices remain deferred to the phases that need them.
- Scope: extend the existing project; do not rebuild it from scratch.

Related context: [Handoff](CODEX_HANDOFF.md), [Architecture](ARCHITECTURE.md), [Roadmap](ROADMAP.md), [Memory](../MEMORY.md), [Structure](../STRUCTURE.md).

This document records the newly requested future direction. Older documents describe the narrower existing implementation. Reconcile them when implementation is authorized; do not treat planned capabilities as already available.

## Product goal

The user supplies a goal. The agent determines the steps, performs validated actions, observes what actually happened, and continues until the goal is verified or genuine user intervention is required.

Examples:

- Find a relevant YouTube tutorial and play it.
- Create an Excel sales dataset, table, pivot table, chart, and saved workbook.
- Inspect an existing workbook and suggest useful analysis.
- Research a topic across multiple pages and create a source-backed deliverable.
- Inspect a selected folder, locate relevant files, and safely perform the requested work.

Prioritize reliability, safety, local-first operation, speed, and extensibility. Preserve the minimal overlay; do not spend substantial time on cosmetics while the agent runtime is incomplete.

## Existing foundation — preserve and reverify

These are historical implementation records, not checks performed when creating this plan:

- Tauri overlay, Ctrl+Space activation, tray lifecycle, and taskbar exclusion.
- Packaged FastAPI sidecar and Ollama readiness/start controls.
- Deterministic shortcuts and bounded structured local-model planning.
- Validated safe application, HTTP(S) URL, and existing-folder launches.
- Whole-plan preflight, per-step SSE events, cancellation, and partial-failure reporting.
- Clarification messages, currently requiring a complete resubmitted request.
- Last recorded verification: 57 backend tests, 6 frontend tests, 7 live planner evaluations, and release build.

Current gaps: no continuous observation/replanning loop, verified browser interaction, Windows control inspection, Excel automation, conversational clarification context, or complete consequential-action approval flow. Launch acceptance is not proof that the user's goal was achieved.

## Architecture and rules

```text
User goal
    ↓
Task runtime + compact working state
    ↓
Observe → Plan next action → Validate permissions → Execute
    ↑                                                 ↓
Continue / Recover / Ask user ← Verify ← Observe result
    ↓
Finish only with supporting evidence
```

- Separate reasoning from execution. The model cannot directly execute arbitrary shell commands.
- Extend a typed capability registry; adding an application should not require rewriting the runtime.
- Prefer native/application APIs, structured Windows UI/accessibility, browser DOM, keyboard shortcuts, vision, then coordinates as a last resort. Choose the relevant structured mechanism for each application.
- Use composable primitives and application knowledge, not giant phrase-matched workflows.
- Keep deterministic fast paths for clear tasks that do not require model reasoning.
- Track the original goal, completion criteria, current plan, observations, completed actions, relevant files/windows, failures, pending approvals, and execution budgets.
- Bound actions, elapsed time, model calls, retries, and replans. Observe before retrying an uncertain side effect.
- Stream concise progress and evidence, never private chain-of-thought.
- Treat webpage, document, and application content as untrusted data, not authority to change the goal or permissions.
- Confirm consequential actions: sending, purchases, important submissions, deletion, software installation, system/security changes, and private-data uploads/publication.
- Never bypass authentication, CAPTCHA, MFA, permissions, or OS security.
- Preserve user files and unsaved application work; prefer new output files and recoverable changes.

## Phase tracker

Use: Not started / In progress / Blocked / Verified complete. A phase is complete only when its exit condition has evidence recorded below.

| Phase | Deliverable | Status | Evidence |
| --- | --- | --- | --- |
| 0 | Audit and baseline | Verified complete | 2026-10-01 audit evidence below |
| 1 | Observation-driven runtime | Verified complete | 82 backend tests, 9 UI tests, 7 live planner evaluations, rebuilt EXE/sidecar smoke check |
| 2 | Capabilities, permissions, observations | In progress | 113 backend tests, 12 UI tests, 7 live planner cases; packaged verification pending |
| 3 | Windows and file foundations | Not started | — |
| 4 | Verified browser workflow | Not started | — |
| 5 | Excel automation | Not started | — |
| 6 | Research and cross-application tasks | Not started | — |
| 7 | Vision fallback and hardening | Not started | — |

### Phase 0 — Audit and baseline

- [x] Read current code, project instructions, documentation, and Git changes.
- [x] Reverify existing tests and packaged application behavior (startup, health, and clarification SSE; not a fresh visual tray/shortcut test).
- [x] Check installed Chrome, desktop Excel, Ollama models, and available hardware.
- [x] Identify reusable modules and integration gaps without replacing working components.
- [x] Establish a rollback checkpoint while preserving user changes (`48acd05` verified; tracked code unchanged during audit).
- [x] Resolve prerequisites for the first slice: Phase 1 uses existing dependencies/model and controlled test adapters; later-phase choices remain explicitly deferred.

Exit condition: verified baseline, evidence-backed gap list, and an actionable implementation checklist.

### Phase 1 — Actual agent runtime

- [x] Introduce structured task state and explicit completion criteria.
- [x] Add observing, planning, executing, verifying, recovering, awaiting-input, completed, failed, and cancelled states (plus explicit unverified outcome).
- [x] Plan the next action from fresh observations instead of blindly executing a fixed plan; current real launch adapter checks prerequisites, generic adaptation is verified with controlled test adapters.
- [x] Keep compact working context rather than resending the full history each iteration.
- [x] Implement execution budgets, bounded recovery, cancellation, and user-intervention handling.
- [x] Test changed observations, uncertain outcomes, failed actions, and unsupported goals.

Exit condition: the loop adapts to observations, stops safely, and cannot claim verified completion based only on action dispatch. Controlled tests establish the runtime contract; real application validation follows in later phases.

### Phase 2 — Capabilities, permissions, and observation contracts

- [ ] Extend the existing registry with typed inputs/outputs, preconditions, postconditions, and verification hooks.
- [ ] Record timeout, cancellation, permission, and retry/idempotency behavior per tool.
- [ ] Add action-specific confirmation requests and responses; changed parameters invalidate prior approval.
- [ ] Represent successful, failed, and unknown outcomes distinctly.
- [ ] Add an application skill/capability interface for Windows, Browser, Files, Excel, Research, and YouTube knowledge.
- [ ] Test malicious external instructions, invalid arguments, stale approvals, and duplicate side effects.

Exit condition: execution is validated, consequential actions wait for approval, and uncertain outcomes cannot trigger blind repeated actions. Application knowledge guides planning but cannot grant permissions.

### Phase 3 — Windows and files

- [ ] List, launch, focus, and inspect applications/windows with stable identity checks.
- [ ] Inspect accessibility/UI Automation controls and invoke supported control actions.
- [ ] Add scoped typing, shortcuts, scrolling, and clipboard operations with privacy safeguards.
- [ ] Detect dialogs, loading, wrong focus, and unsaved-work prompts.
- [ ] Inspect files and folders only within user-selected scope; avoid implicit whole-disk searches.
- [ ] Add safe modification primitives only with previews, overwrite protection, permissions, and recovery where practical.
- [ ] Verify focus and resulting state; avoid fixed coordinates and arbitrary shell execution.

Exit condition: find and focus the correct application, inspect its state, and handle a controlled dialog without guessing or modifying unrelated user work.

### Phase 4 — Browser automation

- [ ] Establish a managed Playwright session; proposed default is a separate agent profile, pending user decision.
- [ ] Add tab/page inspection, navigation, semantic element targeting, extraction, click, fill, scroll, and wait tools.
- [ ] Detect popups, loading, authentication barriers, errors, and stale elements.
- [ ] Verify page transitions and media playback from observed state.
- [ ] Complete the YouTube tutorial goal through dynamic result inspection and selection.
- [ ] Inject a recoverable browser failure and verify observation/replanning.

Exit condition: search for a relevant tutorial, select it, open it, start playback, and verify advancing playback. Do not count an opened URL as success. Do not silently take over personal browser sessions.

### Phase 5 — Excel automation

- [ ] Confirm installed Excel capabilities and select a reliable native integration after a feasibility check.
- [ ] Inspect workbooks, sheets, ranges, headers, data types, and existing structure.
- [ ] Add data/formula editing, sorting/filtering, formatting, and table primitives.
- [ ] Add pivot tables, charts, sheets, save, and save-as primitives.
- [ ] Default to new output files; require approval before overwriting existing work.
- [ ] Create and reopen a sales workbook; verify totals, table, pivot, chart, and saved file.
- [ ] Inspect an existing workbook read-only and propose grounded analysis.

Exit condition: both Excel acceptance tests below pass using real workbook artifacts, not only successful tool return codes.

### Phase 6 — Research and cross-application tasks

- [ ] Gather relevant information from multiple inspected pages and retain source references.
- [ ] Distinguish source findings, inference, and unavailable information.
- [ ] Create requested summaries or workbook deliverables using proven tools.
- [ ] Preserve task context through clarification questions and answers.
- [ ] Verify saved outputs and report their locations and evidence.
- [ ] Keep task working memory separate from optional persistent personal memory.

Exit condition: a research goal produces a source-backed, verifiable deliverable without the user specifying every tool action.

### Phase 7 — Vision fallback and hardening

- [ ] Add screenshots/vision only where structured observation is insufficient and privacy scope is clear.
- [ ] Restrict coordinate actions to last-resort use with fresh screenshots and post-action checks.
- [ ] Test application crashes, stale state, unexpected dialogs, interrupted saves, and cancellation.
- [ ] Evaluate local-model accuracy and latency; consider a larger local model only after measurement and user agreement.
- [ ] Validate packaged behavior, resource usage, and daily-use reliability.

Exit condition: documented realistic reliability results, tested failure paths, and an honest supported-capability matrix. Recovery and testing start in Phase 1, not here.

## End-to-end acceptance tracker

| Test | Required evidence | Status |
| --- | --- | --- |
| YouTube: search Python asyncio tutorials and play a relevant result | Relevant page selected; playback advancing | Not run |
| Excel: create sales data, table, category pivot, chart, and save | Correct totals and structures in the reopened output workbook | Not run |
| Excel: inspect an existing workbook and suggest analysis | Accurate sheet/range findings; no unintended modifications | Not run |
| Research: gather and summarize multiple pages | Inspected sources supporting the summary/deliverable | Not run |
| Recovery: deliberately fail an action | Fresh observation, changed strategy, verified recovery | Not run |
| Cancellation during execution | No new actions dispatched after cancellation is acknowledged; in-flight/completed effects reported | Not run |
| Consequential action | Specific approval required; denial/expiry/parameter changes prevent execution | Not run |

Mocked tests support development but do not establish real application capability. Record actual failures as well as passes. Never invent verification results.

## Decisions pending

- [x] Desktop Excel executable and Excel.Application COM registration are present. Actual automation/licensing/workbook access still require the Phase 5 feasibility test; Excel was not launched during this audit.
- [ ] Is a separate agent-controlled Chrome profile acceptable? Personal-session attachment needs a separate explicit decision.
- [ ] May a larger local model be installed if measurements show the current model is inadequate?
- [ ] Which folders and output locations should be used for realistic file/Excel tests?

Do not treat an unanswered decision as permission. Ask when it becomes necessary; continue only with unaffected, authorized work.

## Maintenance and handoff rules

1. Before working, read this file and confirm the user has authorized implementation.
2. Inspect the current repository; this document is not a substitute for checking actual code and user changes.
3. Update the active phase and checkboxes as work proceeds. Leave unverified work unchecked.
4. After each meaningful implementation slice, record changes, tests/evidence, remaining issues, and the next action.
5. Record a Git checkpoint only when one actually exists and creation is authorized.
6. Synchronize relevant architecture, memory, structure, and handoff documentation when implementation changes them.
7. If the plan changes, record the reason and user decisions rather than silently removing unfinished work.

### Progress log

| Date | Work performed | Verification/evidence | Remaining / next action |
| --- | --- | --- | --- |
| 2026-10-01 | Created this planning and tracking document only | Reviewed the agreed plan and existing context docs; no application tests/builds run | Await explicit approval; then begin Phase 0 |
| 2026-10-01 | User authorized work; completed Phase 0 audit and selected Phase 1 slice | 57 backend tests, 6 UI tests, frontend build, offline cargo check, 7 live planner cases; packaged startup/health/clarification verified | Phase 1: typed task state, observation/verifier interfaces, bounded loop and regression tests. No runtime code changed in Phase 0. |
| 2026-10-01 | Completed Phase 1 generic runtime and real launch-adapter integration; rebuilt and launched EXE | 82 backend tests, 9 UI tests, 7 live local-model cases; release build; packaged health marker and original two-tab request accepted with unverified final outcome | Phase 2 capability schemas/approval lifecycle. Actual Windows, browser DOM, Excel, and vision observation remain later phases. |

### Phase 1 evidence and lessons — 2026-10-01

Implemented:

- `task_state.py`: application-independent task identity, goal criteria, structured outcomes/evidence, compact context, and finite budgets.
- `runtime.py`: pluggable planner/observer/executor/verifier loop; fresh evidence must support every criterion before verified completion. A model's finish message cannot supply evidence.
- `launch_runtime.py`: actual tool-registry integration, full initial preflight, revalidation immediately before dispatch, observed prerequisite checks, bounded local replanning before any effects, and off-event-loop launch calls.
- All current launch tools run through the new runtime. Deterministic clear tasks still avoid model calls. Launches remain explicitly unverified because no page/window observer exists yet.
- UI renders observation/verification/recovery states, updated actions, unknown outcomes, and "Requests sent · not verified" instead of falsely reporting Complete.
- `/health` identifies this backend as `observation-loop-v1`; use it to detect an outdated sidecar when testing.

Verification:

- `python -m pytest -q`: 82 passed (existing Starlette/AnyIO deprecation warning only).
- `npm.cmd test -- --run`: 9 passed; frontend production build passed.
- PyInstaller sidecar build and `npm.cmd run tauri:build -- --no-bundle`: passed.
- `scripts/evaluate-planner.py`: 7/7 passed with installed llama3.2:3b; no tool side effects from this evaluation.
- Launched `src-tauri/target/release/app.exe`; its owned backend returned `runtime: observation-loop-v1`.
- Submitted the original Chrome + GenAI YouTube search + GitHub tab request once to the packaged API: two accepted actions with observe/verify transitions; final `outcome: unverified`, `verified: false`. This verifies launch acceptance, not rendered tabs or playback.
- Packaged/source sidecar SHA-256 matched: `66B4045F17591C9FD3EFF016F2719694B815A695047E28E76804BD6C8CBCDA8F`.
- Controlled adapter tests verify dynamic action choice, observed success, stale/incomplete evidence rejection, bounded recovery, cancellation during dispatch, deadline/model/action/decision budgets, duplicate prevention, malformed tool outcomes, and stream closure after completion.

Lessons applied and next-phase priorities:

1. Launch acceptance is not goal completion. Keep generic runtime evidence separate from tool acknowledgements; add real observers in later phases rather than fabricating results.
2. Exceptions/timeouts after dispatch are not proof that nothing happened. Record unknown, preserve prior effects, observe, and prevent blind replay.
3. A generic loop must not contain Chrome/Excel-specific logic. Those names live in the current launch adapter/planner; Phase 2 should derive available tool schemas from the registry, followed by general Windows capabilities in Phase 3.
4. Refresh state after slow reasoning and revalidate before action. The first local-model evaluation took about 10 seconds cold; warmed corpus cases were about 0.9–2.5 seconds. These are sample observations, not latency guarantees.
5. Mutable target checks must be off the async event loop; cancelling a thread await cannot undo a Windows launch already underway. Tool metadata must make this distinction explicit.
6. Verify terminal state handling: closing a completed stream must not relabel the task cancelled. Include protocol edge cases in future capability tests.
7. Rebuild BOTH Python sidecar and desktop EXE after code phases. A source-only change is not a testable packaged update.

Remaining boundaries: no task persistence/resume, no approval response endpoint yet, no general UI Automation/DOM/Excel adapters, no page reading or video playback verification. Success criteria for launch requests currently retain the original goal text; future capabilities need typed, capability-specific verifiers. Phase 1 establishes the runtime contract, not an ability to perform every computer task.

### Phase 0 evidence — 2026-10-01

Repository:

- Baseline implementation commit verified: `48acd055b8d6577a86972c4df0c42edcb943617d`.
- Initial tracked worktree was clean; this plan was the only untracked file. Preserved it and all existing code.
- Read main API, planner, executor, registry, provider, folder/browser resolution, request models, native lifecycle, UI state/event handling, and context docs.
- No repository AGENTS.md found outside excluded dependency/build directories.

Verification performed:

| Check | Result |
| --- | --- |
| `python -m pytest -q` | 57 passed; existing Starlette/AnyIO deprecation warning |
| `npm.cmd test -- --run` | 6 passed |
| `npm.cmd run build` | Passed |
| `cargo check --offline` in `src-tauri` | Passed |
| `PYTHONPATH=backend; python scripts/evaluate-planner.py` | 7/7 passed against local llama3.2:3b; no tool execution |
| Existing release EXE startup | Launched successfully; packaged backend returned Wingent health response |
| Packaged command `open chrome and something else` | Returned clarification SSE and explicitly took no actions |
| Packaged and source sidecar SHA-256 | Match: `A31D02FE949277122C616E99AEA22FBE77245EC13A97C375C6AB4CDF152D29D3` |

Both Wingent and Ollama were stopped initially. Started the existing release EXE and installed Ollama server for these checks; left them running. No dependencies or models installed, no personal browser session accessed, and no workbook opened. No fresh screenshot/visual verification of the tray or global shortcut was performed. A new release build was unnecessary because application code was unchanged.

Environment observed:

- Windows machine: Intel Core i5-1240P, 12 cores / 16 logical processors, approximately 19.7 GiB reported physical RAM.
- Display adapters: Intel Iris Xe and NVIDIA GeForce RTX 3050 Laptop GPU. VRAM/inference capacity not measured; do not assume a larger model will fit.
- Chrome located at `C:\Program Files\Google\Chrome\Application\chrome.exe`.
- Excel located at `C:\Program Files\Microsoft Office\Root\Office16\EXCEL.EXE`; Excel.Application COM class registered.
- Ollama responds locally on port 11434; installed model list contains `llama3.2:3b` (2,019,393,189 bytes).

Reusable code and confirmed gaps:

| Owner | Preserve | Gap / next integration |
| --- | --- | --- |
| `backend/app/planner.py` | Strict structured output and bounded format repair | Fixed action vocabulary and full plan; no observed task context or next-action decision |
| `backend/app/executor.py` | Whole-plan validation, disconnect checks, honest launch reporting | Sequential loop stops on failure; no observer, verifier, task identity, recovery budget, or goal criteria |
| `backend/app/tools.py` | Allowlisted launchers and permission enforcement | Synchronous executors; no typed observation, retry-safety metadata, verification hooks, or approval lifecycle |
| `backend/app/main.py` | Local API/SSE and existing safe command behavior | Request-scoped state only; no task continuation; broad planning exception path needs separation from post-action errors |
| `backend/app/llm.py` | Local provider interface and schema-based generation | New planner should depend on provider protocol, not concrete Ollama class; explicit call/time/context budgets needed |
| `src/App.tsx` | Minimal UI, step results, cancellation and duplicate-retry prevention | `final` maps to Complete even for accepted-only launches; add verified/unverified and awaiting-input semantics when runtime is integrated |
| `src-tauri/src/lib.rs` | Packaged backend ownership, tray and shortcut | No redesign needed; retain lifecycle regression coverage |

Additional follow-up risks: synchronous tools cannot be forcibly cancelled once an OS call is in progress; readiness currently tests Ollama's port rather than model availability; native sidecar stderr is discarded. Address in the relevant runtime/hardening slices, not by claiming the audit fixed them.

### Phase 1 implementation checklist selected by the audit

Hypothesis: a provider-independent task loop can adapt to fresh observations without replacing current safe launch behavior. Cheapest disconfirming checks: controlled adapter tests showing a changed observation fails to change the next action, or launch acceptance can incorrectly satisfy a verified goal.

1. Add typed task identity/state, explicit success criteria, action records, bounded recent observations, and execution budgets. Keep working state in memory initially; no persistent personal memory.
2. Define narrow planner, observer, executor, and verifier interfaces. Use controlled adapters only in tests; do not expose mocked computer observations in production.
3. Implement observe → decide → validate → execute → observe → verify transitions. Validate fresh targets and permissions immediately before each action; retain full-plan preflight for legacy deterministic commands.
4. Require trusted tool/observer evidence for completion. Model-generated completion text is not evidence. Legacy launches remain accepted-but-unverified until a real observation adapter exists.
5. Bound retries, replans, actions, model calls, context size, and wall time. Unknown side-effect outcomes require observation or user intervention, never automatic repeated dispatch.
6. Preserve cancellation and distinguish failed, cancelled, awaiting-input, unverified, and verified outcomes. Retain partial-action records rather than saying "No actions were taken" after an uncertain execution error.
7. Integrate the runtime with the existing SSE path incrementally; do not redesign the overlay or remove deterministic shortcuts. Expose no new privileged application capability in this phase.
8. Add tests for adaptive next actions, false completion, stale evidence, compact context, unsupported goals, budget exhaustion, cancellation, recoverable failures, and unknown outcomes. Rerun baseline suites before marking Phase 1 complete.

Phase 1 requires no unresolved personal-profile access, larger-model download, or personal workbook selection. The seven live planner cases establish only the old planning baseline, not proof that llama3.2:3b can reliably run the future loop.

### Future update template

```text
Date:
Phase / status:
Changes completed:
Tests and real-world evidence:
Failures / limitations:
Decisions / approvals:
Git checkpoint (if created):
Remaining work:
Next exact action:
```

## Resume instruction

Read docs/AGENT_IMPLEMENTATION_PLAN.md and the existing project context. Check approval status, the phase tracker, and the latest progress entry. Preserve current changes, implement only the authorized slice, verify it, and update this document with evidence. If implementation has not been explicitly authorized, do not start it.
