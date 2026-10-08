# Wingent desktop agent: implementation plan

Updated: 2026-10-08. The sole phase tracker. Inspired by the reference agents; improve the existing project, not a new OS or app-specific automation collection.

## Goal and baseline

`GOAL -> OBSERVE -> DECIDE -> VALIDATE -> ACT -> OBSERVE RESULT -> VERIFY / REPLAN`

The user supplies WHAT; the LLM chooses HOW through general computer input. Retain the overlay, tray, providers and Stop. Application APIs/UIA can improve reliability, but vision and keyboard/mouse remain the fallback for unfamiliar software. Human-like operation means deliberate input and reaction to evidence, not decorative cursor motion.

Current runtime: `wingent-desktop-v3`; latest recovery checkpoint `62be353`. Rollbacks: `0392169` initial adaptation, `e7f5645` before replacement. Old phase completion claims describe a deleted runtime and do not transfer here.

| Area | Actual state |
| --- | --- |
| Brain | Goal outcomes, bounded recent history, screenshot/action batches and launch memory |
| Input | PyAutoGUI primary-screen capture, fractional-coordinate clicks, typing, keys and scrolling |
| Target grounding | Full-screen/window views, frame-local Windows UIA click IDs, coordinate fallback; model misselection and occlusion remain possible |
| Verification | Separate model screenshot review; not independent proof |
| Evidence | One Calculator `72 * 2` pass with independent `144` read-back; one isolated fixture pass |
| Reported failures | Search/playback stops before playing; repeated launches/misclicks; invented `Win+N` app shortcut interrupts Calculator-to-Notepad transfer |

Previous checks: 56 backend, 21 frontend, 3 Rust passes and successful packaging. Those are historical checks, not evidence of arbitrary-task competence. The user reports a new calculation succeeded but the destination-app handoff failed; the transfer remains unverified.

## Reference lessons

See the [source study](REFERENCE_AGENT_STUDY.md) for pinned revisions and exact source owners.

- SOC: small action vocabulary, screenshots between batches, original goal/history, optional OCR/text-box and numbered-target grounding. Its documented Ollama LLaVA path is not proof of better accuracy than the installed model.
- Open-Interface: separate UI/worker/provider responsibilities, shortcuts, small predictable batches and fresh observation after uncertain transitions.
- Do not copy swallowed failures, unlimited retries, arbitrary dispatch, unsafe automatic approvals or model-only success.
- Preserve MIT attribution for vendored source. Review GPLv3 obligations before incorporating Open-Interface code; prefer independently implementing its ideas. Ignored reference checkouts remain unchanged.

## Target contracts

| Responsibility | Required output |
| --- | --- |
| Observe | Timestamp/frame identity, monitor/DPI geometry, foreground/focus, visible targets and optional OCR/UIA facts |
| Decide | Original goal + remaining outcomes + effect history -> next bounded action and expected effect |
| Resolve target | Observed ID/text/region -> validated location; reject stale or ambiguous targets |
| Execute/policy | Check context and risk, obtain necessary approval, send input, release keys/buttons, report dispatch status |
| Verify/progress | Fresh evidence per outcome, preserving completed work across app switches |
| Recover | Inspect no-effect/unknown-effect, change method or ask a genuinely necessary question |

Do not create a framework/module for each row unless implementation needs it. A successful input call is not a successful task.

## Phases

| Phase | Status | Exit gate |
| --- | --- | --- |
| 0. Documentation alignment | Complete | One current plan, explicit limits, obsolete docs removed |
| 1. Observation and target grounding | In progress; crop/mapping slice tested | Correct coordinate/target mapping before further model tuning |
| 2. Input and app transitions | In progress; partial regression fix | Focus-aware typing, real shortcuts and context-bound batches |
| 3. Progress and recovery | In progress; uncertain-input replay and cycle guards tested | No semantic launch/action cycles; multi-step intent retained |
| 4. Evidence-based completion | Planned | Fresh evidence covers every requested outcome |
| 5. Model quality and speed | Planned | Measured latency improvement without lower accuracy |
| 6. General capability extensions | Planned | Extensions share the same policy, cancellation and evidence contracts |
| 7. Packaged qualification | Planned | Repeated held-out task successes through the EXE |

### Phase 1 — Observe and target accurately

Owners: `backend/app/self_operating.py` and adapted input driver; introduce observation helpers only as needed.

- [ ] Add opt-in bounded frame/target/stage diagnostics; do not save personal screenshots by default or commit them.
- [ ] Test physical-pixel to resized-image mapping and Windows scaling. Explicitly reject unsupported monitor layouts.
- [ ] Bind targets to a recent frame/foreground; invalidate after geometry or context changes.
- [x] Add generic UIA/OCR boxes or numbered visible regions, retaining visual fallback for opaque/canvas apps. Implemented UIA IDs, not OCR.
- [ ] Resolve duplicate labels by context/region, not first substring match; request another observation when uncertain.
- [x] Use a legible targeted crop when the overview cannot resolve text. Model-selectable foreground crop implemented; usefulness still depends on model selection.

Gate: independent fixture records 20/20 intended hits per supported scale/layout, including duplicate labels and moved windows. Record native coordinate tests separately from model-selected targets. Do not assume failures are all model quality: check focus, geometry, loading and image legibility first.

### Phase 2 — Reliable input and context transitions

Owners: action schema/driver, loop, overlay handoff if implicated by evidence.

- [x] Validate a supported Windows shortcut vocabulary and declared target; reject invented app-launch chords before input. Contract tests pass; live behavior remains to retest.
- [ ] Observe after opening Search, switching apps or submitting navigation, before subsequent typing. Recheck the intended field, not just the foreground title.
- [ ] Search any installed application through observed results; confirm the selected identity. Reuse already-open apps without duplicate launches.
- [ ] Stop/discard pending batch actions on a new dialog or unexpected focus change. Never silently carry old clicks into a new screen.
- [ ] Keep keyboard sequences distinct from chords; verify Unicode/punctuation and keyboard-layout behavior.
- [x] Align advertised action schema with supported move/scroll/wait/ask primitives. Further gestures require separate contracts/tests.
- [ ] Prefer bounded readiness checks to fixed sleeps. Keep overlay/toast out of input focus and target regions; pause for user interference.
- [ ] Add host risk checks alongside model flags. Routine navigation stays low-friction; sensitive effects need meaningful confirmation. Test Stop and held-key release.

Gate: three repeated launch/type/menu/scroll runs across at least three apps plus a generic fixture; no wrong-window typing, duplicate launch or stuck key. Explicit sensitive-action fixture checks cannot bypass policy by omitting a model flag. A narrow shortcut fix does not complete this phase.

### Phase 3 — Preserve intent and recover from failures

Owners: `task_brain.py`, loop and provider context.

- [ ] Maintain immutable goal/constraints, current subgoal, completed evidence, remaining outcomes, active app and last effect.
- [ ] Associate actions with expected changes; update progress from observations rather than dispatch claims.
- [ ] Distinguish open/minimized/loading/dialog-blocked/closed apps before deciding to launch again.
- [ ] Detect semantic cycles; allow a legitimate repeat only with new evidence and a bounded recovery reason.
- [ ] Recover by observing focus/loading/target, choosing a grounded alternative and verifying. Never blindly replay uncertain typing or consequential input.
- [ ] Batch only predictable stable-context input. Ask for genuine ambiguity/login/important choices, not routine clicks.

Gate: held-out cross-app tasks recover from delayed launch, popup, moved target and failed first click without restarting completed work. Exhausted budgets report specific remaining work, not success. Flexible requests choose a sensible option.

### Phase 4 — Verify the whole task

- [ ] Track evidence for every outcome, including source-app results after switching to the destination app.
- [ ] Prefer UIA/value/file/API read-back; retain explicitly uncertain visual assessment for opaque software.
- [ ] Verify dynamic effects over time. A selected media page alone does not prove matching media is playing.
- [ ] Invalidate stale evidence; distinguish partial, blocked, cancelled, visually assessed and independently verified outcomes.
- [ ] Align UI wording with evidence; `verified:false` must not imply independent success.

Gate: wrong result/item, paused media, untouched destination and missing second-step fixtures never count as verified completion. The Joji task is a regression example, never a production special-case. Cross-app success requires destination evidence too.

### Phase 5 — Measure and improve speed/model quality

- [ ] Measure capture, planning, inference, input, waits and verification; record image/context size, calls and CPU/GPU placement.
- [ ] Compare installed and user-approved alternatives on identical held-out tasks; test actual image understanding, not connectivity alone.
- [ ] Benchmark compact history, crops, OCR caching, stable-context batches and model/context settings. Cache only valid observations.
- [ ] Bound inference-only retries for rate/context/availability errors. No silent paid fallback, model download or replayed input.
- [ ] Fit settings to hardware; extra CPU/RAM cannot guarantee better decisions. Do not silently raise budgets to hide loops.

Gate: compare cold/warm runs and median/tail latency with Phase 1 baseline. Target 25% lower median simple-task duration without reducing success/safety; this is a target, not a promise. Failed/blocked runs do not count as speed wins.

### Phase 6 — General capabilities and continuity

- [ ] Define capability schemas, availability, risk, cancellation and postconditions; advertise only supported capabilities.
- [ ] Add bounded file/terminal/API tools as optional accelerators under the same policy. Terminal execution is not a permission bypass.
- [ ] Keep vision/input fallback for unfamiliar apps, without recreating app-specific planners or the deleted framework wholesale.
- [ ] Load trusted skills only after explicit dependency/license/permission/packaging review; no silent model-controlled installs.
- [ ] Add checkpoint/resume with uncertain-effect reconciliation, never expired approvals or blind action replay.
- [ ] Expand multi-monitor support only after mapping/input tests. UAC/secure-desktop bypass remains out of scope.

Gate: add a capability without changing the core decision loop; demonstrate unfamiliar-app and mixed GUI/tool tasks. Each executor passes cancellation, permission and restart checks.

### Phase 7 — Qualify the release

- [ ] Fix 20 varied tasks across five apps/environments, reserving eight from prompt tuning; repeat each three times.
- [ ] Include text/menu/search-select-play/cross-app/file/recovery tasks using isolated data.
- [ ] Report success, legitimate blocks and failures separately. Target 90% independently checked success on supported non-blocked tasks; safe refusal is not task success.
- [ ] Require zero false verified completions, unauthorized sensitive effects and duplicate consequential effects in this corpus.
- [ ] Build both binaries and verify actual EXE startup, runtime/instance, overlay/toast, approval, Stop and provider failures.
- [ ] Record commit, hashes, model/settings, outcomes, timings and limitations with a rollback point.

A finite pass is not universal competence. Unit, native input, autonomous model and packaged checks are different evidence layers.

## Execution order and progress

Next major slice: reproduce target/focus failures with bounded diagnostics, disconfirm coordinate errors using a generic fixture, then introduce one grounded target path. Validate across apps before tuning the reported music workflow. Small regression fixes can precede the full phase gate; label them partial.

| Date | Slice | Evidence/status | Remaining |
| --- | --- | --- | --- |
| 2026-10-08 | Documentation alignment | Consolidated current baseline, reference lessons and gates; obsolete docs recoverable from Git | Implementation phases open |
| 2026-10-08 | Phase 2 partial: shortcut/navigation | `wingent-desktop-v3`: reject mismatched Windows chords; end batches at Search/switch/Enter and reobserve; advertise all implemented actions. 76 backend tests pass. Pre-code checkpoint `768bbaf`. | No new live cross-app verification; focus/target grounding and remaining phase gates stay open |
| 2026-10-08 | Phases 1/3/5 partial | Foreground crops with physical-coordinate mapping and changed-window input rejection; installed-model dropdown and explicit vision selection; repeated effects trigger fresh completion review. Native fixture passed. First autonomous run produced the right result but failed stopping; after review recovery, the repeated run passed both independent fixture output and clean completion. 91 backend and 24 UI tests pass. | One fixture is not the varied-app/scaling gate. Calculator-to-Notepad and media playback remain unverified on this revision; no full phase completion claim |

For every future slice append commit, hypothesis, narrow check, actual result, live-test scope and build status. Do not create a new report after every edit or mark phases complete from unit tests alone.

### Latest targeting slice (2026-10-08; checkpoint `68fef47`)

- Hypothesis: generic observed control bounds reduce coordinate guessing without app-specific workflows. Full primary-screen observation is now the default; the model can request a foreground crop.
- Implemented bounded read-only Windows accessibility discovery, frame-local click IDs, stale-ID rejection, and semantic repeat detection across regenerated IDs. Pointer clicks still use the real mouse. Optional discovery failures preserve vision fallback.
- Native isolated input fixture passed. The real local model completed Calculator `72 * 9`; an independent UIA display oracle read `648`. Search navigation used observed target clicks; arithmetic used keyboard batching. One malformed model response recovered. This does not independently validate individual keypad clicks.
- Read-only Calculator capture exposed all ten digit buttons and Equals; capture plus discovery measured 2.06 seconds. Model decisions remained substantially slower (first four calls total 55.9 seconds), so no overall speed improvement claim yet.
- Phases 1/3/5 remain partial: varied-app/scaling target accuracy, occlusion safety, model benchmarks and cross-app task gates are still open. Build qualification is separate from these checks.

### Calibration and recovery evidence (2026-10-08)

- Added `scripts/evaluate-targets.py`: independent 20-button fixture with duplicate labels, tested in full-screen and cropped coordinates. No model, screenshots saved, or personal application input is required. Run with `$env:PYTHONPATH='backend'; python scripts/evaluate-targets.py`.
- First live attempt stopped after one hit because foreground identity/geometry changed. No mapping success claimed for that run. Repeat passed all 40 ordered hits at primary resolution 1920x1080. Other scaling/layouts and model-selected targeting remain untested.
- Checkpoints `4d8ef42`, `f2bd78d`, `d027299`, `62be353`: bounded capture retries, scroll/same-title switch boundaries, visible input errors, and uncertain-effect replanning instead of replay/completion review. Latest backend suite: 105 passing; latest UI suite: 25 passing. Recovery gates still require live multi-app fault scenarios.
- No full phase is newly complete: native mapping on one display is only part of Phase 1. Next gate is model-selected target accuracy, moved/occluded controls, and repeated cross-app handoffs—not additional decorative input motion.

### General input capability extension

- Implemented `click` button selection (left/right/middle) and left double-click for both observed IDs and visual coordinates. Host validation rejects invalid counts and incompatible gestures. Non-left/double clicks force a new observation before remaining batch input.
- 114 backend tests pass, including gesture forwarding through target IDs, schema/host rejection, and context-menu batch invalidation. No new model-specific or app-specific workflow was introduced.
- This advances Phase 2 input support; live context-menu/double-click model selection, sensitive-effect policy, and multi-app acceptance gates remain open. Full phase completion is not claimed.

### Target selection investigation — 2026-10-09

- Implemented numbered accessible targets in model screenshots; runtime-ID/name/bounds revalidation before target clicks; exact copied target coordinates also use this check. Every click now ends its predicted batch. Default observation crops the foreground; full-screen overview remains explicit.
- Regression tests reject a control that moves inside the same unchanged window. Markers are image-only, not desktop overlays. Raw coordinate fallback still lacks comprehensive occlusion/semantic-target validation.
- Live local-model text/Confirm fixture passed both independent submitted text and clean completion with the new markers/click boundaries before the automatic-crop adjustment.
- Mouse-only Calculator test failed in full-screen view and was stopped after unrelated clicks. With close-up targeting, the model selected valid IDs but chose Eight instead of the needed Seven; independent display read-back was 8, not 648. Completion review correctly rejected success. This is unresolved model target selection, not a passing phase gate.
- Installed 2B comparison returned empty action output; explicit thinking-off comparison also produced empty output and was stopped. No saved model was switched. Added optional `OLLAMA_THINK` control and a specific error for thinking-only responses, without exposing reasoning traces.
- Phase 1 remains incomplete. Do not describe the native calibration, passing unit tests, or a single fixture as proof of reliable arbitrary-app model targeting. Larger/different models require a controlled comparison, not an untested download recommendation.
