# Wingent Handoff

Updated: 2026-10-02.

## Current instruction

**Scoped implementation and evaluation are authorized by the latest request.** Do not infer permission for broad personal-data access, installations, elevation or consequential actions. Preserve existing changes and use the phase plan as the source of truth.

Start with [AGENT_IMPLEMENTATION_PLAN.md](AGENT_IMPLEMENTATION_PLAN.md). It is the authoritative phase tracker. Read [ARCHITECTURE.md](ARCHITECTURE.md), [ROADMAP.md](ROADMAP.md), [SECURITY.md](SECURITY.md) and [MEMORY.md](../MEMORY.md) as context. The historical plan is archived and must not be used as current scope.

## Product

A general-purpose, local-first Windows computer operator. The user states WHAT; the agent chooses HOW through discovery, planning, observation, action, verification and replanning.

Do not design around individual example applications or hardcode their workflows. Prefer structured APIs/accessibility/DOM; controlled process execution and visual input are planned general mechanisms. Keep the lightweight overlay and tray experience.

Stack: Tauri v2, React/TypeScript/Vite, Python FastAPI/SSE, replaceable local LLM provider with Ollama. Last recorded installed model: llama3.2:3b.

## Current implementation

- Natural requests: main.py → operator.py → AgentRuntime → typed tool registry.
- Operator selects a tool from the registry, generates typed arguments, consumes actual results and decides again.
- Exact simple launch requests retain a model-free compatibility path.
- Registry contracts include permissions, preconditions, timeouts, retry semantics and observation/verification hooks.
- Approval requests are expiring, single-use and bound to task, tool revision and canonical arguments. Model output cannot approve actions.
- File primitives: approved nonrecursive directory listing, fixed 2048-byte UTF-8 pages, and exclusive new-file creation with read-back. The operator rejects invented local file paths and immediately repeated no-effect actions before dispatch.
- Experimental browser tools launch an isolated Chrome profile, inspect bounded page links/media, navigate observed links and test playback progress. Chrome/Edge browser-level CDP worked, but page-level commands exited with `0x80000003` in the restricted session. Normal Chrome fallback requires a newly visible window; no new window was visible here. Host guards reject invented video URLs, unobserved links, reopening the current results page, and Play before media is observed. The local model completed search → correct observed Joji 777 link → Play in a simulated-browser fixture, not a real browser. This is **not a verified working browser agent** and does not control the user's personal Chrome profile.
- Skills: explicitly enabled trusted Python entry points at startup. No model-controlled imports/installations or arbitrary host-plugin loading in the frozen EXE.
- UI supports SSE progress, actions, approval/denial, cancellation, clarification answers and unverified results.
- Packaged Windows app owns its FastAPI sidecar, stays in the tray and uses Ctrl+Space.
- Native shell and overlay now require backend marker `operator-v11`; they refuse a stale/other listener on port 8000 instead of sending tasks to it. The user must quit the old process and restart the new EXE; Wingent does not kill an unknown port occupant.

An initial Win32 child-control adapter offers bounded observation, foreground-at-capture identity and approved, fresh-target click/text plus single navigation-key dispatch with post-action observations. An approved native process adapter can discover executables and run exact arguments with bounded output/time; task cancellation attempts to stop its owned process, but detached descendants remain uncertain. It is not a sandbox. General Windows UI Automation, arbitrary keyboard/mouse and screenshot vision are not implemented. The narrow browser DOM/media slice is experimental. Genuine model clarifications can resume the original task from a short-lived in-memory state without replaying completed actions; state is not durable.

App discovery searches App Paths, matching Start menu shortcuts, PATH and bounded install roots; `application_open` requires exact approval for the discovered path, rejects changed/missing targets and prevents duplicate launches of the same executable within one task. Read-only checks found Notepad and VS Code locally; a real GUI launch/control result was not verified.

## Status and evidence

Phases 0–2 are complete for their bounded recorded contracts. **Phase 3 remains in progress.**

Current slice: 171 backend tests, previous 14 UI tests, 1 Rust contract test and frontend/sidecar/EXE builds pass. Phase 3A's frozen four-app-case corpus passed 1/4 under both default and focused prompt variants; the model did not reliably choose app launch or clarification. See `docs/evaluations/PHASE3A_BASELINE.md`. A controlled sleeping-process cancellation fixture passed; detached descendants are not proven safe. Foreground identity has fixture coverage, but this restricted session enumerates zero visible windows. The installed `llama3.2:3b` reports no vision capability. Two isolated live file variants passed once each in source and again through the frozen sidecar. The installed model passed a simulated-browser Joji 777 sequence, but actual Chrome/Edge page control crashed with `0x80000003` here; real playback is not verified. This does not meet the held-out/repeated reliability gate. Packaged approval denial/replay passed previously; approved Explorer launch returned unknown in this restricted launch environment. The GUI EXE also exited before its backend was reachable when launched hidden here; desktop lifecycle needs an interactive check. A model-only completion assessor had previously hallucinated success and was removed.

Do not treat read-back equality, a model finish message or launch acceptance as whole-goal verification. The model is not proven to be the sole source of failure.

Prior source checkpoint: 18b3255. Release path: src-tauri/target/release/app.exe. Backend health marker in source: operator-v11. Check hashes and current process state before treating a running binary as current.

## Next work

1. Inspect the worktree and relevant code without discarding user changes.
2. Follow Phase 3A/3B: reproducible evaluation, goal/progress state, context retention and evidence-grounded stopping.
3. State an owning code path, falsifiable hypothesis and cheapest disconfirming test before changes.
4. Test each substantive edit narrowly, then evaluate with real tools/model in isolated fixtures.
5. The qwen3.5:4b pull was blocked by outbound network access; do not assume a larger model fixes architectural problems.
6. Update the plan honestly; rebuild both sidecar and EXE for completed code slices and verify the packaged version.
7. Do not add consequential capabilities without their permission, observation and recovery contracts.

Open decisions: network access/model comparison, managed browser profile, personal-data/test scope, screenshot retention, executable plugin trust and process privileges.

## Running reference

Development uses a separately started FastAPI backend on 127.0.0.1:8000, Ollama on 127.0.0.1:11434 and the Tauri development frontend. Packaged app startup manages the backend itself; avoid duplicate services.

Relevant configuration: OLLAMA_BASE_URL, OLLAMA_MODEL, optional OLLAMA_COMPLEX_MODEL, VITE_API_BASE_URL and explicitly enabled WINGENT_SKILLS. Do not ship secrets or silently enable remote model providers.
