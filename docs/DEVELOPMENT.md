# Development

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
- If Ollama is not running, the app will surface a clear error rather than silently failing.
