# Wingent Handoff

Updated: 2026-10-03.

## Current instruction

**Scoped implementation and evaluation are authorized by the latest request.** Do not infer permission for broad personal-data access, installations, elevation or consequential actions. Preserve existing changes and use the phase plan as the source of truth.

Start with [AGENT_IMPLEMENTATION_PLAN.md](AGENT_IMPLEMENTATION_PLAN.md). It is the authoritative phase tracker. Read [ARCHITECTURE.md](ARCHITECTURE.md), [ROADMAP.md](ROADMAP.md), [SECURITY.md](SECURITY.md) and [MEMORY.md](../MEMORY.md) as context. The historical plan is archived and must not be used as current scope.

## Product

A general-purpose, local-first Windows computer operator. The user states WHAT; the agent chooses HOW through discovery, planning, observation, action, verification and replanning.

Do not design around individual example applications or hardcode their workflows. Prefer structured APIs/accessibility/DOM; controlled process execution and visual input are planned general mechanisms. Keep the lightweight overlay and tray experience.

Stack: Tauri v2, React/TypeScript/Vite, Python FastAPI/SSE, replaceable local LLM provider with Ollama. Installed models include `qwen3-vl:4b-instruct` (current default) and `llama3.2:3b`.

## Current implementation

- Natural requests: main.py → operator.py → AgentRuntime → typed tool registry.
- Operator selects a tool from the registry, generates typed arguments, consumes actual results and decides again. Phase 3B adds bounded model notes, a complete task action index, historical-result retrieval, file-page/version coverage and bounded observation refresh. Clarification-supplied names/paths now participate in target grounding.
- Exact simple launch requests retain a model-free compatibility path.
- Registry contracts include permissions, preconditions, timeouts, retry semantics and observation/verification hooks.
- Approval requests are expiring, single-use and bound to task, tool revision and canonical arguments. Model output cannot approve actions.
- File primitives: approved nonrecursive directory listing, fixed 2048-byte UTF-8 pages, and exclusive new-file creation with read-back. The operator rejects invented local file paths and immediately repeated no-effect actions before dispatch.
- Experimental browser tools launch an isolated Chrome profile, inspect bounded page links/media, navigate observed links and test playback progress. Chrome/Edge browser-level CDP worked, but page-level commands exited with `0x80000003` in the restricted session. Normal Chrome fallback requires a newly visible window; no new window was visible here. Host guards reject invented video URLs, unobserved links, reopening the current results page, and Play before media is observed. The local model completed search → correct observed Joji 777 link → Play in a simulated-browser fixture, not a real browser. This is **not a verified working browser agent** and does not control the user's personal Chrome profile.
- Skills: explicitly enabled trusted Python entry points at startup. No model-controlled imports/installations or arbitrary host-plugin loading in the frozen EXE.
- UI supports SSE progress, actions, approval/denial, cancellation, clarification answers and unverified results.
- Packaged Windows app owns its FastAPI sidecar, stays in the tray and uses Ctrl+Space.
- Native shell and overlay now require backend marker `operator-v16`; they refuse a stale/other listener on port 8000 instead of sending tasks to it. The user must quit the old process and restart the new EXE; Wingent does not kill an unknown port occupant. The overlay checks actual Ollama/model readiness and reports missing, stopped or unresponsive states.

An initial Win32 child-control adapter offers bounded observation, foreground-at-capture identity and approved, fresh-target click/text plus single navigation-key dispatch with post-action observations. An approved native process adapter can discover executables and run exact arguments with bounded output/time; task cancellation attempts to stop its owned process, but detached descendants remain uncertain. It is not a sandbox. `screen_inspect` now offers an explicitly approved, in-memory foreground-window capture sent only to a local Ollama vision model; it rejects known password controls, stale/changed identity and non-loopback endpoints. Its description is untrusted, and actual window capture remains unverified here. General Windows UI Automation and arbitrary keyboard/mouse are not implemented. The narrow browser DOM/media slice is experimental. Genuine model clarifications can resume the original task from a short-lived in-memory state without replaying completed actions; state is not durable.

App discovery searches App Paths, matching Start menu shortcuts, PATH and bounded install roots; `application_open` requires exact approval for the discovered path, rejects changed/missing targets and prevents duplicate launches of the same executable within one task. Read-only checks found Notepad and VS Code locally; a real GUI launch/control result was not verified.

## Status and evidence

Phases 0–2 are complete for their bounded recorded contracts. **Phase 3 remains in progress.**

Earlier evidence: operator-v12 passed 178 backend tests; the UI suite previously passed 14 tests. Phase 3A's initial comparison is complete, but `qwen3-vl:4b-instruct` passed only 3/4 in each of two app-corpus runs, failing different cases. See `docs/evaluations/PHASE3A_BASELINE.md`. The vision model described a synthetic red image, but real screen capture/control remains unverified. A controlled sleeping-process cancellation fixture passed; detached descendants remain uncertain. A simulated-browser Joji sequence passed, but actual Chrome/Edge page control crashed with `0x80000003`; real playback is unverified. Packaged approval denial/replay passed previously; approved Explorer launch returned unknown. GUI lifecycle needs an interactive check. A model-only completion assessor had hallucinated success and was removed.

Do not treat read-back equality, a model finish message or launch acceptance as whole-goal verification. The model is not proven to be the sole source of failure.

Phase 3B's bounded working-context contracts are complete. The latest operator-v16 slice passed 200 backend, 15 UI and one Rust test. The installed model completed a fake-browser flexible Joji task in 4 calls/32.89 seconds and exact 777 in 5 calls/26.33 seconds. A trusted observed paused-media postcondition saves a decision for flexible goals; malformed model clarification after an action ends honestly. Actual Chrome page control still crashes here on even a simple `1+1` evaluation, and no real media was tested. Earlier real-model file fixtures passed; the two-page task took 124.22 seconds/11 calls in source. Notes remain fallible and do not verify progress. See the plan for remaining Phase 3C/3D gates.

Release path: src-tauri/target/release/app.exe. Backend health marker in source and packaged sidecar: operator-v16. The source/release sidecar SHA-256 hashes match (`0FAA4747EE6F3FD20A282A9B9A8F2574AE2CDDB3D9197B96E0121DC321A6C079`); EXE SHA-256: `172A903BE154F09248C27CA41A572298A86540B9DFE2ADFD19F612E282A77B2D`. Check running process identity before treating an open app as current. GUI startup and real playback remain unverified here.

## Next work

1. Inspect the worktree and relevant code without discarding user changes.
2. Follow Phase 3C/3D and remaining reliability gates: repeated varied tasks, independent evidence, capability discovery and resilient continuity. Preserve the 3B context/retrieval/completeness contracts.
3. State an owning code path, falsifiable hypothesis and cheapest disconfirming test before changes.
4. Test each substantive edit narrowly, then evaluate with real tools/model in isolated fixtures.
5. The user installed `qwen3-vl:4b-instruct`; its small-corpus gain is inconsistent. Do not assume a visual model fixes planning or desktop access.
6. Update the plan honestly; rebuild both sidecar and EXE for completed code slices and verify the packaged version.
7. Do not add consequential capabilities without their permission, observation and recovery contracts.

Open decisions: managed browser profile, personal-data/test scope, screenshot retention policy, executable plugin trust and process privileges.

## Running reference

Development uses a separately started FastAPI backend on 127.0.0.1:8000, Ollama on 127.0.0.1:11434 and the Tauri development frontend. Packaged app startup manages the backend itself; avoid duplicate services.

Relevant configuration: OLLAMA_BASE_URL, OLLAMA_MODEL, optional OLLAMA_COMPLEX_MODEL, VITE_API_BASE_URL and explicitly enabled WINGENT_SKILLS. Do not ship secrets or silently enable remote model providers.
