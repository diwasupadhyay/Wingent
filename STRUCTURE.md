# Wingent Repository Structure

Updated: 2026-10-02. Current ownership map; proposed work is tracked in docs/AGENT_IMPLEMENTATION_PLAN.md.

## Runtime and capabilities

- backend/app/brain.py — separate local reasoning boundary with the latest approved window image.
- backend/app/computer_tools.py — task/window grants, fresh frames, generic input and sensitive-action checks.
- backend/app/windows_computer.py — Win32 keyboard/mouse, screenshots and Windows UI Automation.
- scripts/evaluate-computer.py / evaluate-native-computer.py — opt-in isolated reasoning and native-app checks.

- backend/app/main.py — loopback API, registry startup and natural-task/shortcut routing.
- backend/app/operator.py — production registry-driven next-tool selection, typed arguments and outcome context.
- backend/app/runtime.py — generic observe/decide/validate/execute/verify loop and lifecycle.
- backend/app/task_state.py — task contracts, observations, evidence, budgets and bounded working state.
- backend/app/task_store.py — bounded, expiring, single-use in-memory clarification continuation.
- backend/app/tools.py — typed registry, permissions, metadata and launch tools.
- backend/app/capabilities.py — argument/output models and trusted capability guidance.
- backend/app/approvals.py — exact-action expiring single-use approval lifecycle.
- backend/app/file_tools.py — approved directory listing, bounded text reads and exclusive new artifacts.
- backend/app/browser_tools.py — experimental agent-owned Chrome page/link/media adapter; live control remains unverified.
- backend/app/window_observer.py — read-only visible-window/process/title enumeration and launch visibility check.
- backend/app/desktop_tools.py — bounded Win32 child-control observation and approved fresh-target input.
- backend/app/process_tools.py — native executable discovery and exact-action-approved bounded process run.
- backend/app/plugins.py — explicitly enabled trusted skill entry points.
- backend/app/launch_runtime.py — shared registry execution/approval adapter, budgeted provider and launch compatibility behavior.
- backend/app/executor.py — compatibility execution and disconnect-aware waits.
- backend/app/planner.py / capability_planner.py — legacy/bounded planning compatibility and evaluation; not the natural-task execution owner.
- backend/app/routing.py / applications.py / folders.py — exact launch shortcuts and approved target resolution.
- backend/app/llm.py / model_routing.py — local provider interface and configured model selection.
- backend/app/models.py — API request/response models.

## UI and packaging

- src/App.tsx / styles.css — minimal overlay, SSE progress, actions, approvals, cancellation, clarification answers and unverified results.
- src-tauri/src/lib.rs — native shortcut, tray/window lifecycle, backend ownership and Ollama controls.
- backend/sidecar.py — packaged backend entry point.
- scripts/build-backend-sidecar.ps1 — PyInstaller build helper.
- src-tauri/target/release/app.exe — last recorded native build location; generated artifact, not a source rollback checkpoint.

## Evidence and documentation

- backend/tests/ and src/App.test.tsx — contract, integration and UI regressions.
- scripts/evaluate-operator.py — opt-in live model plus two isolated real file variants; narrow passes do not satisfy the overall reliability gate.
- scripts/evaluate-browser-operator.py — real local-model reasoning against a simulated browser; never proves actual website/playback behavior.
- scripts/diagnose-browser.py — isolated Chrome/Edge debugger crash probe; no personal profile attachment.
- scripts/evaluate-planner.py — legacy bounded-planner regression corpus; does not validate the current operator.
- scripts/smoke-approvals.py — opt-in packaged approval/denial/replay checks.
- docs/AGENT_IMPLEMENTATION_PLAN.md — sole phase/checklist/evidence/decision tracker.
- docs/ARCHITECTURE.md / ROADMAP.md / CODEX_HANDOFF.md — current design, roadmap index and resume instructions.
- docs/SECURITY.md / API.md / SKILLS.md — trust boundaries, protocol and extension contracts.
- MEMORY.md — concise current context.
- docs/history/AGENT_PLAN_BEFORE_DOCS_REALIGNMENT.md — historical evidence and superseded plan; never active execution guidance.

This ownership map does not itself grant new permissions; the latest user request and tool policy govern execution.
