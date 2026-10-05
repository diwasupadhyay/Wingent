# Wingent Changes

2026-10-05. Source marker: `operator-v25`.

## Routine tasks, provider settings and command bar

Routine computer sessions use an automatic Tauri focus handoff acknowledged through the existing single-use token channel. It is allowed only for the SAFE computer_begin tool with Review off; consequential actions never use this path. This restores the handoff previously coupled to the visible approval dialog.

- Missing pieces: overlay could be selected as a target, routine grants prompted repeatedly, folder paths were guessed, and provider errors lacked useful detail.
- Changes: overlay exclusion/hide, routine session grants, known-folder discovery and directory creation, session-only cloud/local settings, explicit cloud vision opt-in, input lock/clear, removed logo. Ollama schema/grammar rejection gets one JSON-mode retry; all tool proposals still undergo host validation.
- Reference concepts reviewed: Open-Interface core/LLM/model/settings separation and original-request/step context; Self-Operating Computer's repeated screenshot/action loop and model adapters. No reference files modified or copied.
- Verification: mocked provider/privacy/schema fallback tests and UI tests. No live model calls, desktop task execution or paid API tests in this pass, per user request. Original HTTP 400 cause and Windows focus reliability remain pending manual retest.
- Protocol reference: [Ollama structured outputs](https://github.com/ollama/ollama/blob/main/docs/capabilities/structured-outputs.mdx).

## What was missing or broken

- Production exposed two incompatible GUI protocols: a computer grant/frame could be followed by a legacy desktop action requiring a different observation. This explains the reported stale-target class of failure; the exact initial typing error was not supplied.
- Window-only control could lose sight of a new dialog and steal focus back to the old app.
- Empty installed-app searches forced premature stopping, even when the requested app was already running.
- Generic focused UIA Panes erased a visual click target, blocking typing in canvas/custom apps.
- Non-actionable controls were exposed without supported-action metadata. Repeated-input guards could stop without reassessing a completed result.
- The live model harness used a reduced catalogue, masking production tool-selection failures.
- Docs contradicted one another about the current runtime, backend port, computer-control support and phase status.

## Lessons from both references

Actual code reviewed: [comparison and pinned commits](docs/evaluations/SELF_OPERATING_REFERENCES.md). Both use fresh screenshots and structured LLM-selected mouse/keyboard actions in a continuing goal loop. Useful ideas are a small general action vocabulary, current-screen grounding, original-goal retention, deliberate typing targets and re-observation after navigation.

Do not copy their weaknesses: arbitrary method dispatch, blind multi-action sequences, recursive retries, swallowed errors or model-only completion. Wingent keeps strict schemas, local-only pixels, bounded execution, cancellation, scoped grants and exact sensitive-action approvals.

The clones are untouched study material in ignored `references/`, never project dependencies or committed source.

## Implemented changes

- Unified production GUI control under ComputerSession and removed stale capability guidance.
- Added explicitly approved task-long desktop scope with observed-window switching and foreground-dialog following. Narrow window scope remains the default.
- Fixed incomplete app-search fallback and visual input targeting in opaque UIA containers.
- Exposed supported UIA actions and bounded TextPattern text; reject non-actionable invoke requests as known-no-effect.
- Added general hover, bounded wait and same-window drag. Drag always needs exact approval; cancellation releases the button.
- Added bounded duplicate-input reassessment, preserving completed effects and truthful status.
- Repeated-input checks use the actual dispatch window, not a newly opened dialog's post-observation window. Reassessment feedback preserves the model's system prefix for potential cache reuse.
- Updated approval UI to distinguish a task-long control grant from one sensitive action.
- Expanded production-catalogue and native cross-app/gesture evaluations.
- Tightened the model evaluator: a correct app effect followed by a timeout is an end-to-end failure, not a passing run.
- Consolidated documentation into one current plan, architecture, security contract, resume memory and measured evidence. Removed duplicate CHANGELOG, CODEX_HANDOFF and the obsolete app-specific historical plan; their committed versions remain recoverable from Git.

## Verification

See [computer evaluation](docs/evaluations/COMPUTER_OPERATOR.md) for current results, failures, model timings and packaged identity. Native scripted checks, autonomous model runs and packaged UI evidence are intentionally separate.

Final checkpoint: 246 backend, 18 UI and 1 Rust tests pass. Notepad/Calculator/canvas native checks passed. Both binaries were rebuilt; the new EXE was launched and its owned v24 backend/model/tool catalogue checked. The stricter model-driven fixture repeatedly reached the correct app state but failed clean stopping due to a final reasoning timeout; this remains a failing autonomy gate.

## Still needs improvement

The agent is not yet reliably autonomous across arbitrary applications. Local vision is slow; model stopping and recovery are inconsistent. Whole-goal independent verification, unknown-effect reconciliation, durable continuation, process-tree guarantees, whole-desktop/background surfaces, mixed-DPI gestures and secure/elevated desktop remain open. Sensitive actions still need approval. Capture can expose occluding/private content; password detection is incomplete.

Phases are tracked honestly in [the implementation plan](docs/AGENT_IMPLEMENTATION_PLAN.md); these changes do not mark all unfinished phases complete.
