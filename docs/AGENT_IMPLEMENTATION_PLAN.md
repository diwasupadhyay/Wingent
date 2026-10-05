# Wingent Implementation Plan

Updated: 2026-10-05. This is the sole phase tracker. [Changes](../CHANGES.md), [architecture](ARCHITECTURE.md), [security](SECURITY.md) and [evaluation evidence](evaluations/COMPUTER_OPERATOR.md) provide supporting detail.

## Product contract

### Current repair pass (2026-10-05)

- [x] Exclude Wingent from computer targets; hide overlay on task submission.
- [x] Routine computer session starts without approval; retain consequential-action gates and optional Review mode.
- [x] Resolve real Windows known folders and support exclusive directory creation.
- [x] Session-only local/cloud provider settings, explicit cloud screenshot sharing, no stored API keys.
- [x] Remove command-bar logo; lock input while running and clear submitted text.
- [x] Report Ollama rejection details; bounded JSON-mode retry only for schema/grammar rejection.
- [ ] User manual retest: Notepad typing, Calculator-to-Notepad, Desktop folder/file.
- [ ] Establish the actual cause of reported HTTP 400 and Windows focus denial if they recur.

Validation for this pass is lightweight mocked tests/builds only; no live desktop tasks or paid model calls. Reference review: Open-Interface core/model/settings and Self-Operating Computer loop/model API. Applied provider separation and original-goal/fresh-observation continuity; retain host validation of actions.

A local-first general self-operating Windows computer agent. The user states WHAT; the LLM determines HOW. Keep the existing UI and useful tools.

`GOAL -> SEE -> THINK -> ACT -> SEE AGAIN -> VERIFY -> REPLAN`

Applications are environments, not architectural limits. Prefer structured APIs/UIA where reliable; use approved vision and generic input in unfamiliar software. Every effect uses the same permission, cancellation and evidence boundary. Model finish is not verified success.

## Phases and honest status

| Phase | Status | Remaining exit gate |
| --- | --- | --- |
| 0: audit/rollback | Historical bounded completion | Maintain reproducible source/build checkpoints |
| 1: generic runtime | Contract gate complete | Preserve bounded loops, truthful outcomes and cancellation |
| 2: typed tools/approvals | Current contract gate complete | New capabilities must retain exact bound approval and replay checks |
| 3A: model comparison | Initial four-case comparison complete | Broader model choice follows held-out evidence, not intuition |
| 3B: working context | Bounded task/file contracts complete | Durable continuation belongs to 3D/7 |
| 3C: stopping/recovery | In progress | Fresh independent postconditions; reconcile unknown effects without replay |
| 3D: continuity/discovery | In progress | Dependency-aware skill discovery and durable restart/disconnect handling |
| 4: Windows observation/input | Bounded core gate complete | Additional adapters and mutation recovery remain extensions |
| 5: process/code execution | In progress | Prove owned process-tree cleanup including failure/cancellation cases |
| 6: vision/unfamiliar apps | Implemented, broader gate open | Repeated dialog, canvas, occlusion, sensitive-screen and mixed-DPI tests |
| 7: packaged reliability | Open | Repeated mixed-task corpus, resource/latency measurements and rollback evidence |

## Current implementation checklist

- [x] One registry-driven LLM brain consumes original goal, bounded history, fresh screenshot and UIA observations.
- [x] Production uses one GUI protocol; legacy desktop/screen adapters cannot be mixed with computer frames.
- [x] Explicit desktop scope switches observed apps and follows new foreground dialogs; window scope remains default.
- [x] Typed click/type/hotkey/scroll/invoke with one-use frames and identity/focus/geometry checks.
- [x] Add bounded hover/wait and exact-approved same-window drag; real gesture evidence tracked separately.
- [x] Incomplete installed-app discovery checks running windows rather than forcing termination.
- [x] Opaque UIA containers preserve visual input targeting; actionable patterns and bounded document text are exposed.
- [x] Duplicate computer input gets one bounded reassessment; accepted effects are not blindly repeated.
- [x] Original goal, clarification history, host action index, historical-result retrieval and file-page coverage remain intact.
- [x] Production-catalogue unfamiliar-GUI model evaluation, independent fixture output, and native Notepad/Calculator checks.
- [x] Study both external source repositories without copying/executing them; keep clones ignored and unchanged.
- [ ] General independent goal verifier rather than only fixture or tool postconditions.
- [ ] Reliable long-task continuation after interrupted streams/process restarts.
- [ ] Whole-desktop/background surfaces, elevated/secure desktop and mixed-DPI cross-monitor gestures.
- [ ] General destructive file mutation with preview, recovery and stronger filesystem identity handling.
- [ ] Repeated packaged UI/task/approval evaluation across varied unfamiliar apps.

## Next execution slices

1. Use the production tool catalogue in real-model tests; record every wrong choice and stopping failure.
2. Improve observation completeness and latency without weakening freshness checks or masking failures with larger budgets.
3. Add capability-owned postcondition evidence and bounded unknown-outcome inspection.
4. Prove process lifecycle and task continuity; keep executable skill installation outside model authority.
5. Build both sidecar and EXE, verify the exact owned backend and record limitations before each release checkpoint.

## Evaluation gate (not yet satisfied)

- At least 20 varied tasks across three capability families; reserve at least 10 additional cases from prompt tuning.
- Repeat live cases three times with the recorded configuration. Initial target: 90% correct bounded outcomes, distinguishing success from appropriate clarification/refusal.
- Zero unauthorized dispatches, false verified completions or duplicate consequential effects in that corpus.
- Record correctness, stopping, recovery, latency, model calls, approvals and resource use separately.
- Contract tests, native adapter checks, autonomous model tests and packaged tests are distinct evidence layers.
- Never hardcode fixture answers, weaken assertions, raise budgets silently or broadly auto-approve to obtain a pass.

## Evidence and lessons to retain

[3A](evaluations/PHASE3A_BASELINE.md) records inconsistent small-model launch decisions. [3B](evaluations/PHASE3B_CONTEXT.md) records correct file artifacts but high latency. [Computer evaluations](evaluations/COMPUTER_OPERATOR.md) records actual input, visual fallback, production-catalogue failures and fixes. A previous model-only completion assessor hallucinated success after listing a directory and was removed; do not reintroduce that as trusted verification.

[Reference review](evaluations/SELF_OPERATING_REFERENCES.md) compares actual source. Keep the useful screen/action/re-observation idea, but retain bounded host execution, permissions, local privacy and honest uncertainty. Do not claim arbitrary-app competence from these narrow passes.
