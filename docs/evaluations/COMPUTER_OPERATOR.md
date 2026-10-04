# General computer operator evaluation

Date: 2026-10-04. Native input, model reasoning and packaged evidence are separate gates.

## Architecture and sources

The LLM receives goal/history, registry schemas, UI Automation controls and the latest approved window screenshot in one structured generation. Proposals pass through the existing runtime/approval boundary. Each input returns a fresh image. No application workflow is installed in the general adapter.

Architectural inspiration: [Open-Interface](https://github.com/AmberSahdev/Open-Interface), particularly its screenshot/action/re-observation loop and interruption. No code was copied. Wingent uses typed primitives and task/window grants instead of arbitrary method dispatch. [Ollama generate](https://docs.ollama.com/api/generate) supports image inputs and structured output; [Windows SendInput](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput) remains subject to application and integrity-level constraints.

Hypothesis: missing pixels in the decision call and missing general input primitives prevent unfamiliar-app operation. Cheapest check: locate an input in an isolated GUI using the local vision model, dispatch input, and inspect the resulting state.

## Observed failures and fixes

- Restricted enumeration saw no desktop; interactive tests saw real windows. This environment distinction invalidates earlier assumptions that desktop access was unavailable altogether.
- Display scaling shifted clicks. Per-thread physical-pixel DPI awareness fixed them; DWM bounds exclude invisible resize margins.
- Rapid Unicode events corrupted Notepad text. Paced character/modifier delivery fixed the saved result. Typing is limited to 500 characters per action; large documents should use file/API tools.
- Nullable argument schemas had been compacted to `object`. Preserving the actual field types and adding primitive guidance fixes that misleading model input.
- Focus changes correctly block input. Observation-only failures now clear frames and report no input dispatched, allowing bounded replanning instead of inventing unknown application effects.
- Legacy vision probing now uses `/api/show`, not nonexistent capabilities in `/api/tags`.

## Native live evidence

`scripts/evaluate-native-computer.py` creates new test windows only:

- Notepad: replacement text saved and independently read back; exact text matched, allowing a terminal newline.
- Calculator: 7 × 8 entered with general hotkeys; UI Automation returned `Display is 56`.
- Isolated Tk GUI: screenshot-grounded click and typing visibly produced `Hello from Wingent`. Its controls have no useful accessible names, exercising visual fallback.

`scripts/evaluate-computer.py --autonomous` separately tests the full real-model loop and an independent applied-value oracle. Initial runs failed malformed click arguments; subsequent runs reached input but failed after foreground changes. A native pass is not an autonomous pass. Latest run after input-targeting checks: 5 model calls / 67.39 seconds, stopped at the recovery limit after foreground/focus changes; no oracle success or false verified completion. More autonomous reliability work remains.

## Boundaries

Grants authorize broad ordinary UI interaction in one window for one task. Recognized submission/deletion/system-key inputs and sensitive named controls require exact approval. Model classification remains necessary for other consequential semantics: this is not a complete sandbox. UAC/secure desktop, elevated apps, inaccessible dialogs, drag/drop and mixed-DPI multi-monitor behavior remain unsupported or unproven. Whole-goal verification remains explicitly separate from model interpretation.

Production pixels remain in memory and go only to loopback Ollama. The opt-in test harness may save its synthetic window screenshots to ignored `.build/`; personal captures must not be committed.

## Packaged checkpoint

- Backend: 212 tests passed; frontend: 15 passed; Rust backend-version contract: 1 passed.
- PyInstaller sidecar and Tauri `--no-bundle` release build passed.
- Started `D:\Wingent\src-tauri\target\release\app.exe`; `/health` returned `operator-v17` and `/api/model-status` reported ready with `qwen3-vl:4b-instruct`.
- App SHA-256: `837917506117824189B905BDBD357C2DB73F50FB76039A9D4959A1AE4356D887`.
- Source and release-folder sidecar hashes match: `D3A23903944662072EB77ECC0A538F17456355B86BA54F802E71F1C1934B86EB`.
- A final native regression rerun was interrupted by foreground loss after Ctrl+A, before text replacement. Earlier Notepad/Calculator successful results remain recorded, but repeatability under desktop interference is not established.

Use Ctrl+Space then Stop to cancel a task; holding Escape during dispatch also prevents further input. A brief Escape tap during a model call is not a global latched cancel.

Phases 4/6 have a new implemented and partially live-tested slice. Broad Phase 3 autonomy, Phase 5 process-tree guarantees and Phase 7 release reliability are not complete.

## operator-v18 evidence (2026-10-04)

The real local vision model completed the full isolated GUI workflow: observed the window, selected its text field, entered `Hello from Wingent`, clicked Apply, then stopped without repeating the click. The app's own emitted value matched exactly. Six model calls took 103.58 seconds. Wingent's production result remains `unverified` because a changed screenshot alone cannot independently certify arbitrary application semantics; the external test oracle establishes this fixture's outcome.

Native Notepad saved-text read-back and Calculator `Display is 56` both passed twice after Unicode input pacing was raised to 40 ms per code unit. One preceding run had corrupted Notepad text, so this remains a reliability area to monitor beyond the two passing repetitions.

Reasoning changes: reject stale frame IDs and untargeted typing before dispatch; stop before repeating an input after the changed screen; preserve host-observed effects in the final result; pause/resume when Windows denies window focus. A shorter visual prompt and smaller window image retain the correct action sequence but do not make the 4 GiB local vision model fast. The computer adapter is not a general semantic verifier.

Phase 4's bounded Windows-control gate is complete for these applications and failure checks. Phase 3's varied-task reliability, Phase 5 process lifecycle, Phase 6 sensitive-screen policy and Phase 7 release gates remain open.

## Packaged operator-v18 checkpoint

Backend 218 tests, frontend 15 tests and Rust 1 test passed. The PyInstaller sidecar and Tauri `--no-bundle` release build succeeded. The launched `D:\Wingent\src-tauri\target\release\app.exe` reported `/health` runtime `operator-v18`; `/api/model-status` reported ready with `qwen3-vl:4b-instruct`.

App SHA-256: `08CEEC07B8B408DFD3BCBEFA88C54DED7D804088CE06EA291639A4B8BED22D5E`.
Release-folder and source sidecar SHA-256: `197E813D5C53325DE3AF4C11D01160F57B3370E3ED7354FF64051DF7834685D6` (matching).

The positive live fixture is bounded evidence, not a reliability percentage across arbitrary Windows software. Repeated vision decisions took over 100 seconds on the installed hardware; improving latency and robust completion assessment remain Phase 3/7 work.
