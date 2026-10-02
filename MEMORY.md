# Wingent Memory

Updated: 2026-10-03. This is resume context, not a second phase tracker.

## Latest user instruction

Fix the Joji 777 search-only failure while progressing the general agent; do not call Phases 3–5 complete without live exit gates. Preserve honest verification and exact-action approval.

## Direction

General-purpose personal computer agent: user provides the goal, agent discovers tools, reasons, observes, acts, verifies and replans. Examples are not architectural limits. Keep local-first reasoning, minimal overlay/tray, explicit sensitive-action approvals and honest results.

Authoritative tracker: [docs/AGENT_IMPLEMENTATION_PLAN.md](docs/AGENT_IMPLEMENTATION_PLAN.md). Earlier application-specific phases and launcher-only restrictions are superseded. Historical evidence is retained in docs/history/AGENT_PLAN_BEFORE_DOCS_REALIGNMENT.md.

## Implemented and unfinished

- Phases 0–2: recorded baseline, generic bounded runtime and typed/approved tool contracts complete for their stated scope.
- Phase 3: registry-driven next-tool reasoning, typed arguments, outcome feedback, general approved file primitives and opt-in trusted skill entry points exist.
- Phase 3 remains incomplete. The frozen Phase 3A app corpus passes only 1/4 cases under both default and focused prompting with `llama3.2:3b`; the model fails to select launch/clarification reliably. See docs/evaluations/PHASE3A_BASELINE.md. Two isolated file tasks passed once each; this does not meet the varied/held-out reliability gate. A model-only completion assessor had hallucinated success and was removed.
- Fixed 2048-byte read pages replaced model-selected page sizes after a one-byte-read failure.
- Initial Win32 child-control input and scoped navigation keys return bounded post-action observations; visible-window and control observations now include foreground-at-capture identity. Exact-action-approved native process execution has a task cancellation hook and exact-PID fallback; detached descendants remain uncertain. General UI accessibility, arbitrary keyboard/mouse and vision remain unavailable. The narrow browser DOM adapter remains experimental.
- Native application discovery covers App Paths, matching Start menu shortcuts, PATH and bounded install roots; opening requires a fresh task-owned discovery ID, host-bound exact-path approval and identity recheck. Same executable launch is deduplicated within a task. Notepad and VS Code were found read-only, but live GUI launch/control was not verified.
- An experimental agent-owned Chrome DOM/media adapter was added after a reported YouTube playback failure. Chrome and Edge browser-level CDP works, but enabling a page-level session exits with `0x80000003` here; disabling GPU did not help. Normal Chrome fallback showed no new visible window here. Playback remains unverified. The model initially reopened the Joji 777 search URL and tried Play too early; host guards now reject those no-progress actions. It then selected search → observed 777 link → Play in a simulated browser. Browser-control failure stops early instead of wasting model calls.
- After the same old trace recurred, native startup was found to accept any `service: wingent` on port 8000. It now requires the current runtime marker and blocks incompatible submissions instead of silently using a stale backend.
- Initial desktop adapter: observe visible Win32 child controls, then exact-action-approved click or text entry against a fresh window/control identity. This is not visual screen understanding or a claim of general computer control.
- Genuine clarification questions have 15-minute, single-use in-memory resume preserving prior actions and answer history. No durable checkpoints or persistent personal memory; interrupted resumes may be lost.
- Plugin code is trusted native code, not sandboxed. Frozen releases must bundle enabled plugins and metadata.

## Recorded evidence

Current slice: 171 backend, previous 14 UI and 1 Rust contract test pass; frontend, sidecar and native EXE built. Phase 3A app corpus passed 1/4 under both prompt variants. A controlled sleeping-process cancellation fixture passed; scoped keyboard and foreground identity have only fixture coverage because this restricted session enumerates zero visible windows. Installed llama3.2:3b reports no vision capability. Two isolated live file variants passed once with llama3.2:3b, also through the frozen sidecar. A simulated-browser Joji 777 sequence passed with the real model; actual Chrome/Edge page control crashed and playback was not verified. Packaged denial/replay passed previously; approved Explorer launch had an unknown outcome here. Alternative model and Playwright downloads failed because outbound access is blocked.

Latest checkpoint: 18b3255. Current source backend marker: operator-v11. EXE: src-tauri/target/release/app.exe. Check process identity before calling a running binary current.

## Next when authorized

Expand the varied/held-out live corpus; improve explicit remaining-work, observation completeness and independent verification. Harden continuation against disconnect/restart and start read-only structured Windows observation before general UI actions. The current failures do not prove model size is the sole cause.

Every new capability needs typed input/output, declared permissions, target validation, bounded execution, truthful outcomes, observation and verification/recovery behavior. Prefer structured mechanisms, but plan general process and visual fallbacks.

Ask before new personal data/profile access, downloads, executable skill installation, elevation and consequential changes. Rebuild both sidecar and EXE after authorized code slices; record actual evidence and phase status.
