# Development

## Packaged backend
```powershell
python -m pip install pyinstaller==6.16.0
powershell -ExecutionPolicy Bypass -File scripts/build-backend-sidecar.ps1
```

The generated target-triple executable is ignored by Git. Build it before `npm run tauri:build`; Tauri registers it as an external binary. The installed app starts hidden in the tray and starts the backend automatically. Press `Ctrl+Space` or left-click the tray icon to open it.

## Prerequisites
- Node.js 20+
- Python 3.12+
- Rust toolchain for future Tauri packaging work
- Ollama installed locally

## Setup
```powershell
npm install
python -m pip install -r backend/requirements.txt
```

## Run locally
```powershell
npm run dev
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Testing
```powershell
pytest -q
npm test -- --run
npm run build
```

## Notes
- Use the local Ollama model from `.env.example` or set the environment before starting the backend.
- Set `OLLAMA_COMPLEX_MODEL` only to a model already installed in Ollama; otherwise Wingent keeps using `OLLAMA_MODEL`.
- If Ollama is not running, the app will surface a clear error rather than silently failing.
