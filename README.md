# Wingent

Wingent is a Windows computer agent inspired by [OthersideAI's desktop agent](https://github.com/OthersideAI/self-operating-computer). Give it a goal: it takes a screenshot, asks the vision model for actions, moves the mouse/types/presses keys, and looks again.

It is designed as a general computer operator, not a collection of Chrome, Excel, or other app-specific scripts.

Development status: experimental. Calculator has passed a narrow live check, but search/playback and visual targeting remain unreliable. See the [implementation plan](docs/SELF_OPERATING_AGENT_PLAN.md), [reference study](docs/REFERENCE_AGENT_STUDY.md), and [current safety limits](docs/SECURITY.md).

## Features

- Local reasoning and vision through Ollama
- Primary-screen screenshots, visible mouse movement, clicking, Unicode typing, scrolling and hotkeys
- Batched actions across applications through PyAutoGUI
- Local or cloud vision models using the gear icon
- Optional action review, Stop, and PyAutoGUI's screen-corner fail-safe
- Streaming progress, cancellation, failure recovery, tray operation, and `Ctrl+Space`
- Tauri desktop shell with an automatically managed FastAPI sidecar

## Stack

Tauri 2 | React | TypeScript | Python 3.12 | FastAPI | PyAutoGUI | Pillow | Ollama/cloud vision

## Requirements

- Windows 10/11
- Node.js 20.19+
- Python 3.12+
- Rust with the MSVC toolchain
- [Ollama](https://ollama.com/) with `qwen3-vl:4b-instruct`

## Run locally

```powershell
git clone <your-repository-url>
Set-Location Wingent

npm.cmd install
python -m pip install -r backend/requirements.txt
python -m pip install pyinstaller==6.16.0
ollama pull qwen3-vl:4b-instruct

powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/build-backend-sidecar.ps1
npm.cmd run tauri:dev
```

The app runs in the system tray. Press `Ctrl+Space` to open the command bar.

## Build

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/build-release.ps1 -InstallDependencies
```

The executable is created at `src-tauri/target/release/app.exe`.

## Test

```powershell
python -m pytest backend/tests -q
npm.cmd test
cargo test --manifest-path src-tauri/Cargo.toml --lib
```

## Safety and current status

Use the gear icon to select a local model or an HTTPS Chat Completions compatible cloud API. Cloud mode requires your provider's model ID and API key; choose a model supporting images and JSON output for computer tasks. Enable screenshot sharing explicitly for cloud vision. Settings and keys last only for the current app session. Cloud calls send task text/tool results and may incur charges; no cloud service is used by default.

Wingent uses local Ollama by default. Normal interaction runs without window-grant prompts. The model requests confirmation for consequential actions; Review enables approval for every action. Stop cancels input; moving the pointer to a screen corner triggers PyAutoGUI's fail-safe. Secure desktop/UAC is unsupported.

Completion is the model's assessment of the latest screenshot, not independent proof. Reliability and speed depend on the selected vision model. The current engine targets the primary monitor. Optional upstream voice/OCR/SoM source is included but not wired into the command bar.

Upstream source, MIT license and adaptation notes are in [backend/vendor/self_operating_computer](backend/vendor/self_operating_computer). The old execution architecture is recoverable from checkpoint `e7f5645`.
