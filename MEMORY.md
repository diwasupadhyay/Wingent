# Wingent Memory

Updated: 2026-10-05 (Asia/Calcutta). Current source: `operator-v24`.

## Direction and entry points

A general local-first Windows computer agent: user supplies WHAT, the LLM chooses HOW through observation, controlled tools and replanning. Keep the minimal overlay, tray, Ctrl+Space, approvals and cancellation. Do not hardcode app workflows.

Read [the plan](docs/AGENT_IMPLEMENTATION_PLAN.md), [architecture](docs/ARCHITECTURE.md), [security](docs/SECURITY.md) and [changes](CHANGES.md). [Computer evaluations](docs/evaluations/COMPUTER_OPERATOR.md) distinguish native, model and packaged evidence. [Structure](STRUCTURE.md) maps ownership.

## Current state

Natural tasks use `operator.py`, `AgentRuntime` and `AgentBrain`. The brain receives current approved pixels, original goal and bounded context. Production has one GUI protocol: `computer_begin`, `computer_observe`, `computer_action`, `computer_confirm_action`. Legacy desktop/screen adapters remain in compatibility tests only.

Default window scope is narrow. Explicit desktop scope permits task-long switching among observed apps and following foreground dialogs. Input still targets a fresh foreground-window frame. Sensitive effects need approval. Arbitrary-goal verification is incomplete.

Default installed model: `qwen3-vl:4b-instruct`. Do not download or switch models silently. Study-only clones are in ignored `references/`; never modify or commit them.

## Working discipline

Inspect the worktree; preserve useful changes. Identify the owning path, hypothesis and cheapest disconfirming test. Use isolated owned windows/files for live evaluations. Rebuild both sidecar and EXE after code changes. Only terminate project-owned old processes, never an unknown port occupant.

EXE: `src-tauri/target/release/app.exe`. Tauri owns a private per-run backend port and verifies runtime plus instance identity. An unrelated service on port 8000 is not this EXE. Ollama is a separate local service.

Phases 0-2, bounded 3A/3B and bounded Phase 4 have evidence. Broad Phase 3/5/6/7 gates remain open. A successful click or build is not reliable autonomous completion.
