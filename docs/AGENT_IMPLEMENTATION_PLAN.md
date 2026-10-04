# Wingent: General Computer Agent Implementation Plan

Updated: 2026-10-04 (Asia/Calcutta)

## Latest slice: general computer environment

### Phase 4 bounded exit gate met in operator-v18

The tested Windows-control core now spans an isolated unfamiliar GUI, Notepad and Calculator, with app-independent screenshot/UIA/input tools and independent fixture or file/display checks. The local model completed the isolated greeting task in 6 calls / 103.58 seconds; the app's own output matched the requested value. Wingent stopped without repeating Apply and correctly labeled the whole goal unverified because the production computer adapter cannot independently prove arbitrary GUI semantics. Two consecutive native Notepad and Calculator runs passed after paced typing. Focus/geometry/stale-frame failures block input, and Windows focus denial now pauses with a resumable task instead of consuming recovery attempts. This satisfies Phase 4's **bounded general Windows-control exit gate**. It does not certify every application, elevated windows, browser automation or the broader Phase 3/7 reliability gates. See [computer evaluation](evaluations/COMPUTER_OPERATOR.md).

`brain.py` now attaches approved window pixels directly to the LLM's next decision. `computer_tools.py` and `windows_computer.py` provide app-independent UI Automation, screenshot-grounded clicks, typing, scrolling and hotkeys. Files, terminal/process, browser and skills remain peer capabilities, not the product scope. This original implementation uses the screenshot/action/re-observation idea studied in Open-Interface without copying its source.

Completed implementation slice: task/window grants, fresh one-use frames, process/focus/geometry checks, post-action images, cancellation, concurrent-input exclusion, local image transport and overlay handoff. Native isolated-GUI, Notepad and Calculator checks passed. Real-model runs exposed argument and focus-loss failures; the broader autonomous reliability gate remains open. See [computer evaluation](evaluations/COMPUTER_OPERATOR.md) for exact evidence and remaining limits.

Current release: `operator-v17` built and started. Running health/model checks passed; 212 backend, 15 frontend and 1 Rust tests passed. Binary hashes and failed live repeats are recorded in the computer evaluation. Prior v16 evidence below is historical, not the current architecture or roadmap. Do not call all phases complete from narrow input tests or an EXE build.
Current instruction: **Scoped implementation is authorized. The user requested lean checks and will manually test the desktop app. Do not claim phase completion without its real-world exit gate.**
Current implementation phase: **Phase 3A's bounded comparison and Phase 3B's working-context contracts are complete for the tested task/file surface. Phase 3's varied-task reliability gate remains in progress. Phases 4–6 have bounded adapters in progress.**

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
| Natural-task operator | Registry-based tool selection, typed arguments, bounded outcome/constraint/remaining-work notes, complete action index and task-local result retrieval | Repeated/held-out competence remains unproven; previous new-model app corpus passed 3/4 with inconsistent launch behavior |
| Tools and approvals | Typed schemas, permission classes, exact-action expiring approvals, replay protection | Host policy and target-identity hardening remain; metadata is not a sandbox |
| Files | Approved nonrecursive listing, 2048-byte UTF-8 pages, exclusive new text files with read-back | No overwrite/delete/move tools, broad search or robust mutation sandbox |
| Extensions | Explicit startup loading of trusted installed Python skill entry points | No model-enabled installation; arbitrary host plugins in frozen EXE are unsupported |
| Verification | Host evidence gate; file content read-back | No general independent goal verifier; model finish stays unverified |
| Working context | Original goal and clarification history, model notes, all-record provenance index, bounded recent bodies with explicit clipping, retrieval of older results, file page/version coverage | No durable checkpoints; model notes remain fallible, historical results are not fresh observations |
| Computer operation | Discovery of native apps from App Paths, Start menu shortcuts, PATH and bounded install roots; approved exact-path launch, experimental browser DOM, read-only foreground-window identity, bounded Win32 control input and navigation keys with post-action observation, and approved native process execution | No UWP coverage, general UI Automation, browser canvas control, guaranteed descendant cleanup, screenshot understanding or arbitrary keyboard/mouse control |

## 4. Phase tracker

Completed means the recorded phase's bounded exit criteria were met, not that the full product is finished. Checkmarks below refer to recorded implementation, not new testing in this documentation update.

| Phase | Capability layer | Status | Exit gate |
| --- | --- | --- | --- |
| 0 | Audit and rollback baseline | Verified complete historically | Baseline, environment, reusable code and gaps recorded |
| 1 | Application-independent runtime | Verified complete for runtime contracts | Controlled tests establish observation-driven transitions, budgets and evidence gate |
| 2 | Typed capability and approval contracts | Verified complete for current contracts | Validation and exact-action approval/denial/replay protections demonstrated |
| 3 | Reliable general reasoning, working context and discovery | 3A comparison and 3B bounded working-context implementation complete; 3C/3D and overall reliability open | Held-out live tasks progress, recover and stop honestly without fixed workflows |
| 4 | Structured computer observation and action | Complete for bounded Windows-control gate (v18); optional adapter expansion open | Actual targets, observations and effects demonstrated in isolated GUI, Notepad and Calculator; changed focus/identity prevents input |
| 5 | Controlled process/code execution and environment discovery | In progress; executable discovery and approved bounded native execution added | Scoped approved execution, bounded output and controlled process-tree lifecycle |
| 6 | Visual observation and input fallback | Direct multimodal brain and scoped visual input implemented; live failures recorded and fixes tested | Fresh visual targets, scoped input and observed postconditions under failure injection |
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

- [x] Represent requested outcomes, constraints, unresolved questions and output targets as bounded model notes alongside the original goal. Notes are optional model interpretations and never verification or permissions.
- [x] Preserve the full bounded action index with record IDs, statuses and content hashes; explicitly clip recent bodies under a shared budget and retrieve older results with task-local `task_read_result`, without redispatch.
- [x] Retain remaining-work notes and their source record IDs across replanning/clarification; refuse invented record references. Notes can become stale and do not satisfy the independent verification gate.
- [x] Detect immediate and alternating repeated observations; permit one explicitly motivated refresh, or a new observation after an accepted state-changing action. Consequential effects are not replayed.
- [x] Feed retained goal, prior outcomes, clarification answers and results into replanning. Accepted-action guards remain active; clarification-supplied names and paths are now usable.
- [x] Check contiguous file pages of the same observed version before writing a report. Changed versions and missing offsets block premature output; clipped context can be retrieved. This gate covers current UTF-8 file inputs, not arbitrary browser or visual completeness.

3B evidence: contract tests cover history eviction/retrieval, task isolation, source-page gaps/version changes, clarification/resume and alternating cycles. The real local model completed the short fruit fixture and a two-page regional report fixture. The latter needed 11 model calls and 124.22 seconds; only one plan revision was emitted, so notes alone are not a reliable progress assessor. The same paged task passed through the frozen HTTP backend with the full tool catalogue in 172.49 seconds. This is near the 180-second task limit; latency and broad competence remain open. See [3B evidence](evaluations/PHASE3B_CONTEXT.md). Independently verified goal correctness remains a 3C/7 gate.

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

### Phase 4 — Structured computer observation and action (bounded core complete)

The core gate is met by the live isolated GUI plus two native applications and controlled stale/focus checks. The application-specific adapter notes and unchecked expansion items below describe extensions beyond that gate, not evidence that the general Windows primitives were never tested. Browser playback remains unverified and is tracked as a separate adapter/reliability item.

Verified core: window/process identity checks, task-scoped approval, UI Automation observation, fresh screenshot-bound mouse/keyboard actions, safe refusal on changed focus/layout, independent text-file read-back, and actual effects in the isolated GUI, Notepad and Calculator. The following unchecked items are additional adapters or broader mutation capabilities, not requirements for this bounded core gate.

Peer adapters, not an application-by-application roadmap:

Current experimental browser slice: an isolated temporary Chrome profile, loopback DevTools page observation, bounded link navigation and HTML media time-progress check are registered through the same tool contracts. It does not attach to the user's normal Chrome profile. Both Chrome and Edge reached a debugger endpoint, then exited with `0x80000003` in this restricted session; adding startup delay did not fix it. A normal Chrome search-window fallback now requires a **new** visible window rather than mistaking an existing Chrome window for success. No new window was visible here, so the result remains unknown—not playback success. A read-only `observe_windows` tool reports visible top-level process/title observations. The host now rejects invented video URLs and link indices that were not returned by the latest live browser observation. A real-model fixture with a simulated browser chose search → observed link → play correctly, but this only tests reasoning. **Do not claim real browser playback works yet.** The next check must run in an interactive desktop session against a disposable page, then YouTube if network access works. Do not mark Phase 4 complete from source tests or build success.

The exact "Joji 777" request exposed a second planning failure: with a simulated search page containing the requested result, the model reopened the same results URL and attempted Play before reaching media. Host no-progress checks now reject those proposals, and the local model then selected search → the observed 777 link → Play in the simulated fixture. The browser-level DevTools socket answers, but enabling a page-level session crashes Chrome/Edge here with `0x80000003`; disabling GPU did not help. Direct YouTube fetch is also blocked by outbound network policy in this execution environment. These observations isolate the reasoning fix from the unresolved live browser-control failure. When browser control fails, the operator now stops with a page-control limitation instead of spending more model calls. None of this verifies actual playback.

Initial Windows-control slice: `observe_windows` exposes visible window IDs and foreground identity at capture time (0 if unlisted); `desktop_observe` reads bounded Win32 child controls and whether the selected window is foreground. Approved `desktop_click_control` and `desktop_type_text` require the latest observation ID, recheck window PID/executable/title and control class/text/rectangle, reject stale targets and password fields, and return accepted dispatch with a bounded post-action window observation. `desktop_press_key` adds approved, single-key navigation/activation (Enter, Escape, Tab, arrows and similar) scoped to a fresh observed window; it is not arbitrary keyboard access. This is a general adapter, not application-specific automation. Window titles, foreground identity and Win32 child controls do not expose Chromium DOM or canvas pixels. Cross-process focus, control behavior and resulting effects still need interactive validation; no claim of full computer control follows from this slice.

Native application discovery now reads Windows App Paths, matching Start menu shortcut targets, PATH, and bounded standard install roots. It returns local native `.exe` matches only. `application_open` binds a fresh, task-owned discovery ID to the exact executable path in the approval request; it rechecks file identity and refuses duplicate launch of the same path within one task. A missing/unresolvable shortcut or UWP app may still be absent. This is discovery and launch dispatch, not verified application control. The local model's [Phase 3A app corpus](evaluations/PHASE3A_BASELINE.md) still fails to choose launch reliably, so do not claim the natural-language app workflow works end to end.

- [x] Windows: discover applications/windows with stable identity and focus checks in the bounded same-integrity surface.
- [x] Accessibility: inspect controls/state and dispatch supported actions; stale/changed targets are rejected. Cross-window dialogs require a new grant.
- [ ] Browser: managed sessions, semantic DOM targets, navigation/extraction and observed postconditions.
- [ ] Application APIs: discover and use native structured interfaces where installed and appropriate.
- [x] Files: scoped directory listing, bounded text reading, exclusive new-file creation and read-back. Broad search and mutation remain extensions.
- [ ] Input/clipboard: explicit target/focus, privacy scope and post-action checks.
- [ ] Mutation: previews, overwrite protection, backups/recovery and exact permissions where appropriate.
- [x] Register implemented adapters through the same contracts; return typed observations and limitations.

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
| Backend contracts/regressions | 200 passed for operator-v16 source |
| UI tests | 15 passed |
| Sidecar/frontend/native release build | v16 sidecar, frontend and no-bundle EXE built; source/release sidecar hashes match |
| Packaged approval/denial/replay | Denial and replay passed; approved Explorer launch returned unknown in this restricted session, so that smoke scenario did not pass |
| Real model, isolated file workflow | Current short fruit and two-page regional fixtures passed in source; two-page fixture also passed via operator-v13 frozen HTTP backend/full catalogue in 172.49 seconds. Whole-goal verification remains false |
| Real model, simulated browser task | Search → observed Joji result → play selected in order; not a real browser/playback test |
| General desktop/browser/terminal/vision | Win32, bounded process and approved screen-description adapters exist; screen capture/browser remain unverified in an interactive desktop |

Current live-model measurements: an isolated fake-browser flexible Joji goal selected search, an observed result, then Play in 4 calls/32.89 seconds after the safe postcondition shortcut; a named Joji-777 goal selected the correct observed result and Play in 5 calls/26.33 seconds. These timings vary across runs, and reported media progress is fixture data, not real Chrome playback. An isolated file-report goal passed read-back in 4 calls/54.81 seconds. None meets the varied, repeated, real-desktop exit gate. Chrome page control also crashes on a minimal isolated `1+1` CDP evaluation, including a headless trial; this is not a prompt-parsing failure.

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

Current EXE path: `src-tauri/target/release/app.exe`; source and native shell require health marker `operator-v16`. Prior Git source checkpoint: `680a3fd` (speed/readiness implementation).

The current backend suite passed 200 tests, UI suite 15 tests, and the Rust contract test passed. The latest slice rejects redundant plain-browser launch for an explicit media goal, sends flexible selected/observed paused media through the existing Play tool without another model call, and keeps exact-title selection model-driven. It also preserves partial results when the model returns an unusable empty clarification after an action. These are general browser-capability/postcondition rules, not artist-specific routes. Broader independent task verification remains open. Prior Phase 3A app comparisons were inconsistent (3/4 in each new-model run, different failures). Actual screen capture, desktop action, browser playback, GUI startup and the broader Phase 3 reliability gate remain unverified in this restricted session. The prior sleeping-process cancellation fixture passed, but descendant cleanup remains uncertain. Do not claim a working general desktop operator.

The `operator-v16` frozen sidecar and no-bundle EXE built successfully. The source and release-folder sidecar SHA-256 hashes match: `0FAA4747EE6F3FD20A282A9B9A8F2574AE2CDDB3D9197B96E0121DC321A6C079`. The release EXE SHA-256 is `172A903BE154F09248C27CA41A572298A86540B9DFE2ADFD19F612E282A77B2D`. The frontend build passed. This verifies packaged artifacts, not GUI startup or live browser playback.

The frozen backend served the current health marker and passed the paged report evaluation through HTTP with the full registered catalogue. The initial test-process cleanup was denied by the restricted shell; after checking its exact PID/path, elevated cleanup stopped only the launched test tree and freed port 8000. This backend check does not validate the GUI lifecycle.

## 10. Next execution slices

The following general-agent priorities supersede the older browser-first list:

1. Build/start the v17 EXE and verify its packaged backend identity and ordinary lifecycle.
2. Improve goal-driven reasoning across unfamiliar isolated applications; measure decisions separately from actual effects and independent result checks.
3. Add capability-owned completion evidence, bounded unknown-effect reconciliation and robust dialog/focus recovery without blindly replaying input.
4. Expand mixed UI/file/process/browser evaluations, latency measurements and held-out tasks. Browser/media is one environment, not the roadmap.
5. Harden durable continuation, UAC/UIPI limitations, occlusion, multi-monitor behavior and semantic approval boundaries.

### Historical v16 browser investigation (not current execution order)

1. Establish the exact running build/backend identity and reproduce the reported Joji failure in an interactive Windows session. Record the request, selected tools, browser process/window, page observations and final outcome. Do not infer the cause solely from an old trace or a passing unit test.
2. Isolate why managed Chrome/Edge control exits in this environment. Check launch flags, profile ownership, browser logs and a disposable local page; compare with a normal interactive session. If CDP remains unreliable, design a replaceable structured browser adapter rather than a phrase-specific workaround. Do not attach to the personal browser profile without a separate scope decision.
3. Make the browser task work end to end on the disposable page, then on a real video result where network and consent allow: discover a real link, navigate, observe the page, attempt play, verify time progression and recover/stop honestly. Vary wording and targets so the test demonstrates agent behavior, not a Joji-specific command.
4. Expand the isolated live corpus toward 20 varied tasks and 10 held-out variants across available capability families. Record latency, calls, artifacts, failures and terminal outcomes. Use the completed 3B context/completeness contracts while adding independent capability-owned postconditions and improving the near-budget packaged latency.
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
| 2026-10-03 | Completed bounded Phase 3B working-context contracts: planning notes, result provenance/retrieval, page/version coverage, alternating-cycle guard and clarification grounding; rebuilt operator-v13 | 187 backend and 1 Rust test pass; frontend/sidecar/EXE builds pass and hashes match. Short/paged source tasks passed; paged frozen-backend task passed in 172.49 seconds. Broad reliability, speed, GUI/screen/browser control and independent completion remain open. |
| 2026-10-03 | Combined tool selection/typed arguments with guarded fallback, lazy guidance, media-progress stop guard, model-catalogue readiness diagnostics and retry, clarification preservation, operator-v15 rebuild | 195 backend, 15 UI and 1 Rust test pass; sidecar/EXE built and hashes match. Installed model passed isolated fake-browser Joji task (5 calls/20.33 seconds) and fruit file task (4 calls/54.81 seconds). Real Chrome playback and broad Phase 3 exit gate remain unverified. |
| 2026-10-03 | Added a guarded flexible-media postcondition to save a model call, rejected redundant plain Chrome launch for media work, and made malformed post-action clarification stop honestly; operator-v16 rebuild | 200 backend, 15 UI and 1 Rust test pass. Qwen fake-browser any-Joji task passed in 4 calls/32.89 seconds and exact Joji-777 in 5 calls/26.33 seconds. Browser page CDP crashes on a minimal evaluation here, so real playback and Phase 3/4 exit gates remain open. |

For each future slice record: authorization, phase/checklist items, hypothesis, changes, tests, live failures, packaged version, actual checkpoint, remaining risks and next action.
