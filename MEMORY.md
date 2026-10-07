# Wingent handoff

Updated: 2026-10-08. Current runtime: `wingent-desktop-v3`.

Build a general self-operating Windows computer agent within this project, not a new OS or app-specific workflow collection. Keep the overlay, tray, provider settings and Stop.

The sole phase tracker is [SELF_OPERATING_AGENT_PLAN.md](docs/SELF_OPERATING_AGENT_PLAN.md). Read it with [security](docs/SECURITY.md) and the [reference study](docs/REFERENCE_AGENT_STUDY.md) before implementation.

## Current reality

- `self_operating.py` runs screenshot/model/action batches. `task_brain.py` supplies outcomes, launch memory and separate visual completion review.
- The adapted vendored PyAutoGUI driver supplies primary-screen capture and input. OCR/UIA target grounding is not active.
- Calculator `72 * 2` passed one live-model run with independent `144` read-back. Joji playback still fails through inaccurate targeting, lost progress and repeated actions. General autonomy is not reliably working.
- Visual review remains model judgement, not independent proof; final events can say `completed` with `verified:false`.
- Latest backend checks: 76 passing. Shortcut validation rejects invented app-launch chords; navigation ends the predicted batch for re-observation. Calculator-to-Notepad transfer still needs live retesting. Previous frontend/Rust checks are historical until rerun.
- Default model: `qwen3-vl:4b-instruct`. Do not download/switch models silently.

## Next work

Start Phase 1 observation/target calibration, not another prompt-only patch or hardcoded YouTube routine. Check actual effects across apps. Distinguish native input, autonomous reasoning and packaged behavior. Mark phases complete only against their evidence gates.

Old phase statuses belong to a deleted runtime; do not carry them forward. Checkpoints: `e7f5645` before replacement, `0392169` initial replacement, `1d934d5` current code baseline. Deleted docs remain recoverable from Git.

Leave ignored `references/` unchanged. The licensed SOC copy in `backend/vendor/self_operating_computer/` is intentionally tracked; preserve its license/provenance.

For future code releases use `scripts/build-release.ps1`. Keep `wingent-backend.exe` beside `src-tauri/target/release/app.exe`. Tauri owns a private backend port and validates runtime/instance identity; never kill an unrelated port occupant.
