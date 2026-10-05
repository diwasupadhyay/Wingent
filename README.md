# Wingent

Wingent is an experimental, local-first AI agent for Windows. Give it a goal and it uses a local vision-language model to observe applications, choose tools, perform controlled mouse/keyboard actions, inspect the result, and replan.

It is designed as a general computer operator, not a collection of Chrome, Excel, or other app-specific scripts.

## Features

- Local reasoning and vision through Ollama
- Screen, mouse, keyboard, scrolling, hotkeys, drag, and Windows UI Automation
- Cross-application and dialog handling through scoped computer sessions
- Typed tools for applications, files, processes, and optional browser operations
- Explicit approval for computer-control grants and consequential actions
- Streaming progress, cancellation, failure recovery, tray operation, and `Ctrl+Space`
- Tauri desktop shell with an automatically managed FastAPI sidecar

## Stack

Tauri 2 | React | TypeScript | Vite | Python 3.12 | FastAPI | Ollama | Windows APIs

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
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/build-backend-sidecar.ps1
npm.cmd run tauri:build -- --no-bundle
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

Wingent uses local Ollama by default, validates fresh window/frame identity, and asks before sensitive effects. Routine control starts without approval unless Review is enabled. Password fields, secure desktop/UAC, and arbitrary elevated applications are not supported.

This is active experimental software. The tested computer-control primitives work across isolated Notepad, Calculator, and custom UI fixtures, but reliable autonomous completion across arbitrary applications is still in progress. Review requested actions and do not use it unattended for destructive, financial, security-sensitive, or irreversible work.

See [CHANGES.md](CHANGES.md), [security boundaries](docs/SECURITY.md), and the [implementation plan](docs/AGENT_IMPLEMENTATION_PLAN.md) for current evidence and limitations.
