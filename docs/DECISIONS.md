# Design Decisions

Updated: 2026-10-05.

- **General brain and tools:** natural tasks use registry-driven next-action reasoning, not fixed app workflows. Exact launch shortcuts remain compatibility fast paths.
- **See after acting:** current approved pixels plus UIA facts enter the brain; actions return fresh one-use frames. App APIs are optional accelerators.
- **One GUI protocol:** production excludes legacy desktop/screen adapters with incompatible IDs/grants.
- **Explicit scope:** window scope is default; desktop scope is task-long approved cross-window access. Sensitive effects still need exact approval.
- **Freshness before speed:** no blind batches across screen transitions. Enforce typed input, process/focus/geometry checks, cancellation and post-observation.
- **Evidence before completion:** model finish and input dispatch are not independent verification. Unknown effects cannot be blindly replayed.
- **Local provider:** Ollama is replaceable; pixels stay in memory and go only to loopback, with no silent remote fallback.
- **Minimal overlay:** retain tray, shortcut and useful progress/approval/output without a full chat UI.
- **Owned backend:** Tauri starts a frozen sidecar on a per-run private loopback port and verifies instance identity, never adopting arbitrary port-8000 services.
- **Trusted extensions:** installed entry points need deliberate enablement and packaging; the model cannot import/install code.
- **Read-only references:** ignored external clones are study material. Do not adopt their arbitrary method dispatch, unbounded retry or model-only completion as host policy.
