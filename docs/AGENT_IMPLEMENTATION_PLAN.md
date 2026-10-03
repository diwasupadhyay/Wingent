# Wingent: General Computer Agent Implementation Plan

Updated: 2026-10-03 (Asia/Calcutta)
Current instruction: **Scoped implementation is authorized. The user requested lean checks and will manually test the desktop app. Do not claim phase completion without its real-world exit gate.**
Current implementation phase: **Phase 3A's bounded comparison is complete; Phase 3's reliability gate remains in progress. Phases 4–6 have bounded adapters in progress, not validated full-computer control.**

## 1. Product direction

Wingent is a local-first, general-purpose personal computer AI agent. The user states WHAT they want; the agent determines HOW, discovers suitable capabilities, performs controlled actions, observes results, and continues until the goal is verified or it must ask for help.

The intended experience is an AI operator for the user's PC, not a command parser with a growing list of phrases. It should handle unfamiliar goals and combine available applications, browser, files, code, APIs and desktop controls as needed. The user should not need to name a tool or break a goal into commands. A result is useful only when the requested outcome happened, not when a tool merely accepted a request.

Applications, websites, documents, coding projects and workflows are examples, not separate products or predefined automations. The architecture must support unfamiliar combinations of tasks without adding phrase-specific routes or rewriting the core runtime.

Core behavior:

`GOAL → UNDERSTAND → PLAN → OBSERVE → ACT → OBSERVE RESULT → VERIFY → REPLAN`

Prefer application APIs, Windows APIs/accessibility and structured browser automation when appropriate. Use controlled process/code execution and, eventually, scoped visual input when structured mechanisms are insufficient. No mechanism bypasses permissions.

Preserve the minimal Tauri overlay, tray, shortcut, local provider interface, useful tools, approval system and generic runtime. Voice, cloud reasoning and persistent personal memory are not prerequisites for this plan.

## 2. Authority and document ownership

- This file owns phases, checklists, acceptance gates, decisions and next work.
- [Architecture](ARCHITECTURE.md) distinguishes implemented components from intended design.
- [Roadmap](ROADMAP.md) is a short index, not a competing tracker.
- [Handoff](CODEX_HANDOFF.md) and [Memory](../MEMORY.md) contain concise resume context.
- [Security](SECURITY.md), [API](API.md) and [Skills](SKILLS.md) describe boundaries and contracts.
- [Historical snapshot](history/AGENT_PLAN_BEFORE_DOCS_REALIGNMENT.md) preserves earlier evidence and superseded application-specific phases. It is not active guidance.

The current user request authorizes scoped implementation and lean verification. It does not waive per-action approvals or grant broad personal-data, installation or elevation access.

## 3. Actual baseline, not promised capability

| Area | Implemented | Remaining limitation |
| --- | --- | --- |
| Desktop shell | Minimal overlay, Ctrl+Space, tray, taskbar exclusion, packaged backend ownership | Daily-use/lifecycle hardening remains |
| Agent runtime | Observe/decide/validate/execute/verify, budgets, cancellation, bounded recovery | Generic runtime correctness is not real-world task competence |
| Natural-task operator | Registry-based next-tool selection, separate typed argument generation, actual result feedback; frozen Phase 3A app corpus | Repetition, incomplete interpretation and unreliable stopping in live evaluation; current model passed only 1/4 app cases in each prompt variant |
| Tools and approvals | Typed schemas, permission classes, exact-action expiring approvals, replay protection | Host policy and target-identity hardening remain; metadata is not a sandbox |
| Files | Approved nonrecursive listing, 2048-byte UTF-8 pages, exclusive new text files with read-back | No overwrite/delete/move tools, broad search or robust mutation sandbox |
| Extensions | Explicit startup loading of trusted installed Python skill entry points | No model-enabled installation; arbitrary host plugins in frozen EXE are unsupported |
| Verification | Host evidence gate; file content read-back | No general independent goal verifier; model finish stays unverified |
| Working context | Bounded request-local goal/results/observations; short-lived in-memory clarification resume | No durable task checkpoints or personal memory; interrupted resumes may be lost |
| Computer operation | Discovery of native apps from App Paths, Start menu shortcuts, PATH and bounded install roots; approved exact-path launch, experimental browser DOM, read-only foreground-window identity, bounded Win32 control input and navigation keys with post-action observation, and approved native process execution | No UWP coverage, general UI Automation, browser canvas control, guaranteed descendant cleanup, screenshot understanding or arbitrary keyboard/mouse control |

## 4. Phase tracker

Completed means the recorded phase's bounded exit criteria were met, not that the full product is finished. Checkmarks below refer to recorded implementation, not new testing in this documentation update.

| Phase | Capability layer | Status | Exit gate |
| --- | --- | --- | --- |
| 0 | Audit and rollback baseline | Verified complete historically | Baseline, environment, reusable code and gaps recorded |
| 1 | Application-independent runtime | Verified complete for runtime contracts | Controlled tests establish observation-driven transitions, budgets and evidence gate |
| 2 | Typed capability and approval contracts | Verified complete for current contracts | Validation and exact-action approval/denial/replay protections demonstrated |
| 3 | Reliable general reasoning, working context and discovery | In progress; bounded 3A app comparison recorded | Held-out live tasks progress, recover and stop honestly without fixed workflows |
| 4 | Structured computer observation and action | In progress; file, experimental browser and first approved Win32 control adapters present, but live control not yet verified | Correct targets, meaningful observations and verified effects across independent adapters |
| 5 | Controlled process/code execution and environment discovery | In progress; executable discovery and approved bounded native execution added | Scoped approved execution, bounded output and controlled process-tree lifecycle |
| 6 | Visual observation and input fallback | In progress; approved foreground-window capture and local model description, no visual action | Fresh visual targets, scoped input and observed postconditions under failure injection |
| 7 | Cross-capability reliability and release readiness | Planned | Reproducible mixed-task and safety evidence from the packaged application |

Order: stabilize Phase 3 before broadening autonomous effects. Phase 4 read-only feasibility work may be an explicitly approved parallel slice, not permission to skip the reasoning gate. Testing, security and packaging apply throughout; they are not postponed until Phase 7.

The phases are capability and reliability gates, not separate Excel/browser/Chrome products. Phase 3 and the browser portion of Phase 4 must be assessed together against a real end-to-end task: a good decision sequence with a simulated browser does not count if the actual desktop browser never opens or the media never plays.

## 5. Phase details and completion checklists

### Phase 0 — Audit and baseline

- [x] Inspect repository, environment, existing behavior and reusable components.
- [x] Record baseline test/build evidence and rollback points.
- [x] Document scope, limitations and deferred access decisions.

Historical evidence: 57 backend tests, 6 UI tests, build checks and packaged startup/clarification checks. See archive for details.

### Phase 1 — Generic runtime

- [x] Add task identities, goal criteria, actions, observations, outcomes and evidence.
- [x] Implement observing, planning, execution, verification, recovery and terminal states.
- [x] Enforce time/action/model/recovery budgets and cancellation.
- [x] Prevent model finish or launch acceptance from becoming verified completion.
- [x] Test stale evidence, changed observations, unknown effects and duplicate side effects.

Historical evidence: 82 backend tests, 9 UI tests, rebuilt release and launch-adapter smoke checks. Real desktop control was not part of this exit gate.

### Phase 2 — Capability and permission contracts

- [x] Add typed inputs/outputs, prerequisites, timeout/cancellation/retry metadata and observer/verifier hooks.
- [x] Derive model tool schemas from registered capabilities.
- [x] Bind approvals to task, tool revision and canonical arguments.
- [x] Require explicit approval responses; reject denial, expiry, replay and changed arguments.
- [x] Distinguish accepted, known-no-effect and unknown outcomes.
- [x] Verify packaged approval/denial/replay flow using controlled safe actions.

Historical evidence: 113 backend tests, 12 UI tests and packaged safety checks. This does not certify malicious plugin isolation or every future consequential tool.

### Phase 3 — Reasoning, context, discovery and honest completion

Owning paths: `operator.py`, `task_state.py`, `runtime.py`, registry/skill contracts and evaluation harnesses.

Already present:

- [x] Select tools dynamically and generate arguments against their schemas.
- [x] Feed actual tool outcomes back into subsequent decisions.
- [x] Support trusted opt-in skills without changing core action enums.
- [x] Preserve host approvals and bounded execution for model-selected actions.
- [x] Demonstrate general file discovery/read/create primitives with real artifacts.
- [x] Record failing live evaluations rather than declaring success from unit tests.

3A — Diagnose and measure before choosing a model:

- [x] Freeze an initial repeatable app baseline corpus and record model/configuration, latency, calls, outcomes and failure reasons. Scope is four isolated app cases, not the full capability surface; see [Phase 3A baseline](evaluations/PHASE3A_BASELINE.md).
- [x] Define separate schema, argument, context-loss, planning, observation and termination failure classes in the harness; final app run produced planning and termination failures.
- [x] Compare default and focused tool guidance against the same four cases. Both passed 1/4; no measured improvement. Broader/held-out comparison remains open.
- [x] Compare the user-installed `qwen3-vl:4b-instruct` against `llama3.2:3b` on the same initial corpus. The new model passed 3/4 versus 2/4 in a post-clarification run but missed launch on a repeat; see [Phase 3A baseline](evaluations/PHASE3A_BASELINE.md). This closes the initial 3A measurement checklist, **not** the Phase 3 reliability gate. Hardware utilization was not benchmarked.

3B — Goal and progress representation:

- [ ] Represent requested outcomes, constraints, unresolved questions and output targets explicitly.
- [ ] Preserve essential facts and action history when context is compacted; expose truncation and provenance.
- [ ] Track remaining work without treating a model-generated checklist as verified truth.
- [ ] Detect no-progress cycles and repeated observations; require a changed reason/state before continuing.
- [ ] Replan remaining work rather than restarting accepted actions.
- [ ] Verify observation completeness before using data to produce outputs.

3C — Evidence-grounded stopping and recovery:

- [ ] Match goal criteria to capability-owned, fresh postcondition evidence where possible.
- [ ] Distinguish dispatch acceptance, observed artifact validity and whole-goal correctness.
- [ ] Where independent verification is unavailable, report bounded partial/unverified results instead of inventing certainty.
- [ ] Ground final summaries in actual results and identify incomplete work.
- [ ] Recover from known-no-effect failures; inspect unknown outcomes before any retry.
- [ ] Test misleading tool content, false model completion and premature finish.

3D — Task continuity and skill discovery:

- [x] Continue a task through a genuine clarification without replaying earlier effects (in-memory, 15-minute, single-use continuation).
- [ ] Separate user questions, action approvals and capability-unavailable states.
- [ ] Discover capability availability/dependencies and retrieve relevant guidance without flooding context.
- [ ] Keep enabling/installing executable skills outside model authority; define packaging/version compatibility.
- [ ] Add explicit scoped read grants only with a defined lifetime, boundaries and revocation; current per-action approval remains until then.

Exit gate: the proposed evaluation gates in section 6 pass for this bounded tool surface, including unfamiliar inputs, injected failure, missing capability, correct stopping and no false verified completion. No application-specific phrase logic may be added to make the corpus pass.

### Phase 4 — Structured computer observation and action

Peer adapters, not an application-by-application roadmap:

Current experimental browser slice: an isolated temporary Chrome profile, loopback DevTools page observation, bounded link navigation and HTML media time-progress check are registered through the same tool contracts. It does not attach to the user's normal Chrome profile. Both Chrome and Edge reached a debugger endpoint, then exited with `0x80000003` in this restricted session; adding startup delay did not fix it. A normal Chrome search-window fallback now requires a **new** visible window rather than mistaking an existing Chrome window for success. No new window was visible here, so the result remains unknown—not playback success. A read-only `observe_windows` tool reports visible top-level process/title observations. The host now rejects invented video URLs and link indices that were not returned by the latest live browser observation. A real-model fixture with a simulated browser chose search → observed link → play correctly, but this only tests reasoning. **Do not claim real browser playback works yet.** The next check must run in an interactive desktop session against a disposable page, then YouTube if network access works. Do not mark Phase 4 complete from source tests or build success.

The exact "Joji 777" request exposed a second planning failure: with a simulated search page containing the requested result, the model reopened the same results URL and attempted Play before reaching media. Host no-progress checks now reject those proposals, and the local model then selected search → the observed 777 link → Play in the simulated fixture. The browser-level DevTools socket answers, but enabling a page-level session crashes Chrome/Edge here with `0x80000003`; disabling GPU did not help. Direct YouTube fetch is also blocked by outbound network policy in this execution environment. These observations isolate the reasoning fix from the unresolved live browser-control failure. When browser control fails, the operator now stops with a page-control limitation instead of spending more model calls. None of this verifies actual playback.

Initial Windows-control slice: `observe_windows` exposes visible window IDs and foreground identity at capture time (0 if unlisted); `desktop_observe` reads bounded Win32 child controls and whether the selected window is foreground. Approved `desktop_click_control` and `desktop_type_text` require the latest observation ID, recheck window PID/executable/title and control class/text/rectangle, reject stale targets and password fields, and return accepted dispatch with a bounded post-action window observation. `desktop_press_key` adds approved, single-key navigation/activation (Enter, Escape, Tab, arrows and similar) scoped to a fresh observed window; it is not arbitrary keyboard access. This is a general adapter, not application-specific automation. Window titles, foreground identity and Win32 child controls do not expose Chromium DOM or canvas pixels. Cross-process focus, control behavior and resulting effects still need interactive validation; no claim of full computer control follows from this slice.

Native application discovery now reads Windows App Paths, matching Start menu shortcut targets, PATH, and bounded standard install roots. It returns local native `.exe` matches only. `application_open` binds a fresh, task-owned discovery ID to the exact executable path in the approval request; it rechecks file identity and refuses duplicate launch of the same path within one task. A missing/unresolvable shortcut or UWP app may still be absent. This is discovery and launch dispatch, not verified application control. The local model's [Phase 3A app corpus](evaluations/PHASE3A_BASELINE.md) still fails to choose launch reliably, so do not claim the natural-language app workflow works end to end.

- [ ] Windows: discover applications/windows with stable identity, focus checks and capability availability.
- [ ] Accessibility: inspect controls and state; invoke supported actions; handle dialogs/loading/stale controls.
- [ ] Browser: managed sessions, semantic DOM targets, navigation/extraction and observed postconditions.
- [ ] Application APIs: discover and use native structured interfaces where installed and appropriate.
- [ ] Files: scoped discovery/read/search, artifact inspection and safe modification primitives.
- [ ] Input/clipboard: explicit target/focus, privacy scope and post-action checks.
- [ ] Mutation: previews, overwrite protection, backups/recovery and exact permissions where appropriate.
- [ ] Register all adapters through the same contracts; return typed observations and limitations.

Exit gate: general primitives work across at least two independent structured adapters in controlled fixtures. Changed identity/focus, unexpected dialogs and inaccessible targets fail safely. Real user data/profile access needs its own scope decision.

Browser acceptance example (a test, not a hardcoded route): given an unfamiliar request to play a music video, the agent must identify an actual search result, open the correct browser/session, navigate to a real observed result, establish that the selected page and media are present and that playback progresses, or report the precise point of failure. Placeholder IDs, accepted launch requests, simulated results and an unrelated open browser window do not satisfy this gate. Repeat with varied artists and wording, plus missing-network, consent-dialog and stale-target cases.

### Phase 5 — Controlled process and code execution

Initial slice: `process_discover` finds native executables on PATH without running them. `process_run` accepts an exact absolute native executable, argument vector and local working directory, requires host approval for that exact action, inherits only a small environment allowlist and caps output. Timeout and task cancellation now request termination of the owned process tree; if Windows tree termination fails, the exact launched child PID is killed. Both remain unknown outcomes because detached children or earlier effects may remain. This is not a sandbox, guaranteed descendant cleanup, installation workflow or independent goal verifier. Interactive and packaged checks are still needed.

- [x] Discover native executables on PATH without running arbitrary discovery scripts; version probing remains a separate approved action.
- [x] Use explicit executable, argument vector, working directory and minimized inherited environment for the initial native adapter.
- [ ] Define command preview/approval, interpreter/script rules and trust boundaries; no claim that shell=false is a sandbox.
- [ ] Bound runtime/output and own process trees across timeout AND cancellation; cancellation now reaches the owned child, but detached descendants and concurrent launch/termination races still need stronger lifecycle tests.
- [ ] Inspect files/diffs before modifications; verify requested outcomes independently of exit code.
- [ ] Handle tests/builds and project repair in disposable workspaces before personal repositories.
- [ ] Require approval for installations, elevation, system/security changes, downloads and externally visible effects as appropriate.
- [ ] Record recovery limits; do not promise rollback for irreversible changes.

Exit gate: controlled fixtures demonstrate execution, failure, timeout, cancellation, output bounds and artifact verification, without affecting unrelated processes/files.

### Phase 6 — Vision and general input fallback

The user installed `qwen3-vl:4b-instruct`; Ollama reports completion, vision and tools. Wingent now defaults to it for local reasoning, while `OLLAMA_MODEL` remains an override. On a synthetic in-memory red image the local vision API answered “red.” Resource check: RTX 3050 Laptop GPU with 4 GiB VRAM and about 19.7 GiB physical RAM; latency ranged from about 4 to 29 seconds across the small app corpus. `screen_inspect` is an initial approved observation adapter: it takes a recent `desktop_observe` window identity, requires the window to remain foreground, refuses known Win32 password controls and non-loopback Ollama endpoints, captures a bounded window region into memory, and sends PNG bytes only to local Ollama. Wingent does not save or return the screenshot; the model's description is untrusted and unverified. No browser/canvas password-field redaction, coordinate input, independent pixel postconditions or live interactive Windows capture is validated. This restricted session enumerates zero visible windows.

- [x] Assess installed local vision-provider availability, synthetic-image response, latency and local resource cost. No further download was performed here.
- [ ] Establish complete screenshot scope/redaction/retention policy and capture provenance; initial per-window approval/in-memory/no-disk/known-password guard exists, but browser/canvas secrets are not reliably detected.
- [ ] Prefer structured targets; use fresh screenshots only when those mechanisms are insufficient.
- [ ] Bind coordinate/input actions to current window/display identity and recheck focus.
- [ ] Observe each meaningful effect; detect stale screens, layout changes and obstructing dialogs.
- [ ] Require confirmation for consequential visual actions exactly as for APIs.
- [ ] Stop at authentication, MFA/CAPTCHA and permission barriers; request user intervention.

Exit gate: controlled layout/focus changes and missed targets are detected; no stale coordinate dispatch or unobserved success claim. Vision is fallback, not a replacement for reliable structured tools.

### Phase 7 — Mixed-capability reliability and release readiness

- [ ] Compose unrelated capabilities for held-out goals without application-specific workflow code.
- [ ] Add durable, privacy-scoped task checkpoints and safe restart/reconciliation of unknown in-flight effects.
- [ ] Verify research/source provenance and deliverable content, not only artifact existence.
- [ ] Exercise crashes, disconnects, cancellation, permission denial, missing dependencies and interrupted writes.
- [ ] Validate startup/quit, tray/shortcut, packaged skill availability, diagnostics and resource usage.
- [ ] Make version/build identity and supported-capability limitations visible.
- [ ] Establish regression corpus, release/rollback procedure and realistic reliability reporting.

Exit gate: packaged evaluation meets recorded targets, safety failures are resolved, known limitations are published, and users can identify the exact tested build. This is a bounded release claim, never a guarantee to perform every possible PC task.

## 6. Proposed evaluation contract

These are release-direction gates; the current small live fixtures do not satisfy them.

- Baseline: at least 20 varied tasks across three capability families as adapters become available; keep at least 10 additional cases held out from prompt tuning.
- Phase 3 starts with available tools plus controlled extension fixtures; do not wait for all future adapters to measure reasoning.
- Vary names, paths, wording, tool combinations, missing information and requested outputs. Examples are fixtures, never runtime routes.
- Repeat live cases three times with the same recorded configuration. Initial target: at least 90% correct bounded outcomes, with supported successes distinguished from appropriate clarification/refusal.
- Mandatory safety gate: zero unauthorized dispatches, false verified completions or duplicate consequential effects in the evaluation suite. Passing a finite suite is not proof of universal safety.
- Record semantic correctness, completion/stop behavior, recovery, latency, model calls, approval count and resource use separately.
- Preserve failed cases. Do not weaken assertions, raise budgets silently, hardcode answers or use broad automatic approvals to obtain a pass.
- Mocked contracts, real adapter checks, live-model reasoning and packaged tests are separate evidence layers.

| Current evidence layer | Last recorded result (2026-10-03) |
| --- | --- |
| Backend contracts/regressions | Current suite pending final count for operator-v12; focused screen/model tests passed |
| UI tests | 14 passed |
| Sidecar/frontend/native release build | Passed; new sidecar and EXE hashes below |
| Packaged approval/denial/replay | Denial and replay passed; approved Explorer launch returned unknown in this restricted session, so that smoke scenario did not pass |
| Real model, isolated file workflow | Fruit and supplies fixtures passed once each in source and again through frozen sidecar; both remain unverified whole-goal outcomes |
| Real model, simulated browser task | Search → observed Joji result → play selected in order; not a real browser/playback test |
| General desktop/browser/terminal/vision | Win32, bounded process and approved screen-description adapters exist; screen capture/browser remain unverified in an interactive desktop |

## 7. Known failures and lessons

The installed llama3.2:3b produced redundant questions, empty actions, repeated discovery/reads, premature finish and budget exhaustion. Separate tool selection/typed argument generation improved tool use but did not solve reliability. A model-only completion assessor hallucinated success after a directory listing and was removed. This slice retained latest distinct action results, gave one bounded corrective prompt for an identical repeated action, and stopped unverified at model-call exhaustion. Two isolated live variants then produced expected artifacts, but this is far below the held-out/repetition gate.

Packaged testing exposed model-selected one-byte reads. Page size is now host-controlled at 2048 bytes. A later source trial read complete data and created the expected artifact, but still repeated actions until the call limit.

These results do not isolate model capacity as the sole cause. Goal representation, context retention, tool guidance and verification also need measured work. Do not infer whole-goal success from matching written bytes.

## 8. Decisions awaiting the user

- Alternative local model: the user installed `qwen3-vl:4b-instruct`, and the initial same-corpus comparison is recorded. Repeated and held-out tests are still required before claiming reliable autonomy.
- Browser profile/session ownership: separate managed profile proposed; personal-session attachment not approved.
- Personal folders, repositories and output locations for realistic testing: scope must be explicitly selected.
- Screenshot/clipboard access and retention: a per-capture, foreground-window-only local vision slice exists. Broader capture, redaction, retention guarantees and visual input authority remain undecided.
- Plugin installation, terminal privileges and software/system changes: approve exact scope when needed.

No open decision grants blanket authority. Continue with safe, local and isolated fixtures; the newly installed model enables bounded comparison, not general desktop access.

## 9. Build, history and rollback record

Recorded implementation checkpoint: `999671c` — general operator groundwork and live evaluation gaps. Earlier checkpoints: `98b95bf` (runtime), `75e2109` (audit), `48acd05` (launcher baseline). These identify source history, not bundled binaries.

Current EXE path: `src-tauri/target/release/app.exe`; source and native shell require health marker `operator-v12`.

The current backend suite passed 178 tests. Phase 3A's bounded model comparison is complete: the newly installed `qwen3-vl:4b-instruct` passed 3/4 in two corpus runs but failed a different case on repetition; `llama3.2:3b` passed 2/4 with host clarification. A synthetic in-memory image was interpreted correctly by the local vision model. Actual screen capture, desktop action, browser playback, packaged startup and the broader Phase 3 reliability gate remain unverified in this restricted session, which enumerates zero visible windows. The prior sleeping-process cancellation fixture passed, but descendant cleanup remains uncertain. Do not claim a working general desktop operator.

The `operator-v12` sidecar and no-bundle EXE built successfully; the source and release-folder sidecar hashes match (`26283131CD7FEEDD863FA2EEA9B2B7B71681E2FF3ABDCD8253841F9E70471D92`). The release EXE SHA-256 is `7ADB5E5C3D0E33F0C170E06E91A0D7C99294FC359AFAC964AB4CDF26ABB003B2`. The one Rust contract test and frontend build passed.

## 10. Next execution slices

1. Establish the exact running build/backend identity and reproduce the reported Joji failure in an interactive Windows session. Record the request, selected tools, browser process/window, page observations and final outcome. Do not infer the cause solely from an old trace or a passing unit test.
2. Isolate why managed Chrome/Edge control exits in this environment. Check launch flags, profile ownership, browser logs and a disposable local page; compare with a normal interactive session. If CDP remains unreliable, design a replaceable structured browser adapter rather than a phrase-specific workaround. Do not attach to the personal browser profile without a separate scope decision.
3. Make the browser task work end to end on the disposable page, then on a real video result where network and consent allow: discover a real link, navigate, observe the page, attempt play, verify time progression and recover/stop honestly. Vary wording and targets so the test demonstrates agent behavior, not a Joji-specific command.
4. Expand the isolated live corpus toward 20 varied tasks and 10 held-out variants across available capability families. Record latency, calls, artifacts, failures and terminal outcomes. Add explicit remaining-work/observation-completeness state and capability-owned postcondition checks based on measured failure classes.
5. Harden task continuation across dropped streams/restarts and unknown effects. Then extend structured Windows/accessibility observation and action, controlled processes, and visual fallback under their phase-specific safety gates. Rebuild and test the sidecar and EXE after each authorized code slice; never mark a phase complete from source tests alone.

At each slice, distinguish four outcomes: model selected sensible actions; tools actually executed; the computer visibly changed as intended; and the user's whole goal was independently verified. A failure at any layer stays a failure or an explicitly partial result, not a success claim.

## 11. Maintenance log

| Date | Change | Execution/evidence |
| --- | --- | --- |
| 2026-10-01 | Baseline/runtime/approval work | Historical records in archive |
| 2026-10-02 | General operator groundwork | Checkpoint 999671c; 123 backend / 12 UI tests; live gate failed |
| 2026-10-02 | Replaced conflicting trackers with capability-based phases; aligned related docs | Documentation only; no implementation, tests, builds, downloads or commits |
| 2026-10-02 | Retained distinct action context, bounded duplicate correction, honest budget stopping, in-memory clarification continuation and two live fixture variants | 132 backend / 13 UI tests; frontend, sidecar and EXE built; fruit and supplies passed in source and frozen sidecar; model comparison blocked by network; desktop lifecycle/Explorer smoke not verified in restricted session |
| 2026-10-02 | Began browser observation/playback adapter, visible-window fallback/observer, and blocked invented paths/URLs/indices and repeated no-effect actions after the Joji failure | 145 backend / 13 UI tests; real model passed simulated-browser search → observed link → play; Chrome and Edge CDP processes crashed with 0x80000003 here; sidecar and EXE rebuilt with operator-v4; no real playback verified |
| 2026-10-02 | Diagnosed repeated old Joji trace as a possible stale-backend attachment: native shell previously accepted any service named Wingent on port 8000 | Native health now requires `operator-v4`, refuses occupied incompatible ports, and UI blocks submissions with a specific error; Rust contract test and 14 UI tests pass. Final EXE rebuilt, release-folder sidecar hash matches source. Real Chrome playback remains unverified. |
| 2026-10-02 | Reaffirmed general PC-operator direction, corrected current authorization, and reordered proposed work around real desktop/browser evidence | Documentation only. No implementation, test, launch, download or build was authorized or performed for this revision. Phase statuses unchanged. |
| 2026-10-02 | Reduced agent-owned browser startup to its existing page target and bounded navigation within a longer tool timeout | Focused browser tests: 7 passed. Sidecar and no-bundle release EXE built; source and release-folder sidecar hashes match. Real interactive Chrome/YouTube playback and the EXE desktop lifecycle are not verified in this slice; Phase 4 remains in progress. |
| 2026-10-02 | Added general Win32 child-control observation and approval-gated click/text dispatch with freshness and identity checks; changed packaged runtime marker to operator-v5 | Full backend suite: 148 passed; Rust contract test: 1 passed; sidecar and EXE builds passed, sidecar hashes match. Live desktop input, screenshots/vision and full agent reliability remain unverified; Phases 3 and 4 stay in progress, Phase 6 is not complete. |
| 2026-10-03 | Added approved bounded native process discovery/execution, removed unused routing detector and redundant application-specific capability hints; rebuilt operator-v6 | Backend suite: 153 passed; Rust contract test: 1 passed; sidecar/EXE build passed and sidecar hashes match. Timeout is unknown; cancellation/detached children, packaged execution and goal verification remain unverified. Phase 5 in progress. |
| 2026-10-03 | Reproduced Joji 777 planning failure; added host checks for reopening an observed page and playing before media exists; retained accessible-name links; made browser-control failure stop early; rebuilt operator-v7 | 156 backend and 1 Rust test pass; sidecar/EXE builds pass and sidecar hashes match. Local model now follows the correct observed 777 result in a simulated browser. Chrome/Edge page-level DevTools still crashes here; direct EXE launch had no reachable backend. Real playback and Phase 3/4 exit gates remain unverified. |
| 2026-10-03 | Added task-bound process cancellation hook with exact-PID fallback and bounded post-action Win32 observation; rebuilt operator-v8 | 159 backend and 1 Rust test pass; sidecar/EXE builds pass and sidecar hashes match. Owned sleeping child stopped in a controlled cancellation test. Detached children, packaged cancellation, real UI effects, vision and live browser playback are not verified. Phases 3–5 remain in progress. |
| 2026-10-03 | Added exact-action-approved navigation key input bound to a fresh observed window; rebuilt operator-v9 | 161 backend and 1 Rust test pass; sidecar/EXE builds pass and sidecar hashes match. Changed/stale window fixture rejects dispatch. Live keyboard delivery, vision and browser playback remain unverified; Phase 4 remains in progress. |
| 2026-10-03 | Added read-only foreground-window identity to visible-window/control observations and warned operator not to infer pixels; rebuilt operator-v10 | 162 backend and 1 Rust test pass; sidecar/EXE builds pass and sidecar hashes match. Unknown foreground is explicit; restricted session sees zero visible windows. Installed Ollama model is text-only; screen-pixel understanding remains unavailable. |
| 2026-10-03 | Added bounded installed-app discovery, exact-path approved launch, same-app duplicate guard and frozen Phase 3A app corpus; rebuilt operator-v11 | 171 backend and 1 Rust test pass; sidecar/EXE builds pass and hashes match. Local model passed only 1/4 app cases in either guidance variant, so Phase 3A remains open. Native Notepad and VS Code were found read-only; real interactive launch/control and screen vision remain unverified. |
| 2026-10-03 | Installed-model comparison, host clarification for unnamed apps, default local vision model, approved bounded `screen_inspect`, and operator-v12 rebuild | 178 backend and 1 Rust test pass; frontend/sidecar/EXE builds pass and sidecar hashes match. Phase 3A bounded comparison complete; broader Phase 3 and live Phase 6 gates remain open. Synthetic image interpreted; actual capture/control unverified because no visible windows exist in this restricted session. |

For each future slice record: authorization, phase/checklist items, hypothesis, changes, tests, live failures, packaged version, actual checkpoint, remaining risks and next action.
