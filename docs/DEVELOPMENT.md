# Development

Requires Windows, Python 3.12+, Node.js, Rust/MSVC toolchain and separately installed Ollama. Default model is `qwen3-vl:4b-instruct`; only configure installed models.

## Setup and browser-only development

```powershell
npm.cmd install
python -m pip install -r backend/requirements.txt
$env:PYTHONPATH = 'backend'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Run `npm.cmd run dev` in another terminal. `VITE_API_BASE_URL` overrides the browser-development API URL. Environment examples are configuration references; do not assume files are automatically loaded.

## Native development and release

Build the sidecar first; Tauri development and release own their own per-run private backend port, independent of a manually started port-8000 service.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/build-backend-sidecar.ps1
npm.cmd run tauri:dev
```

Release:

```powershell
npm.cmd run tauri:build -- --no-bundle
```

Output: `src-tauri/target/release/app.exe` with its adjacent backend binary. Rebuild the sidecar before the EXE when Python changes. Stop only exact project-owned old processes blocking the build. Start the EXE; it stays in the tray, opened with Ctrl+Space. Closing the overlay hides it; tray Quit exits.

## Verification

```powershell
python -m pytest backend/tests -q
npm.cmd test
cargo test --manifest-path src-tauri/Cargo.toml --lib
```

Interactive, opt-in isolated checks (do not use your mouse/keyboard during execution):

```powershell
$env:PYTHONPATH = 'backend'
python scripts/evaluate-native-computer.py
python scripts/evaluate-gestures.py
python scripts/evaluate-computer.py --autonomous
```

The native scripts control only newly created test windows. The model harness approves only its fixture's window grant, and checks output independently. Native scripted success is not autonomous model success.

Keep reference clones untouched under ignored `references/`. Never stage screenshots, fixture documents, model data, credentials or reference code.
