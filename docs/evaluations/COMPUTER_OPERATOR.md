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
