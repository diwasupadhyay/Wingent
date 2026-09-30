# Troubleshooting

## The backend says Ollama is unavailable
- Make sure Ollama is installed and running.
- Verify the server responds at `http://127.0.0.1:11434/api/tags`.
- Pull a model such as `llama3.2:3b` if needed.

## The UI does not connect to the backend
- Confirm the backend is running on port 8000.
- Ensure `VITE_API_BASE_URL` matches the service address.

## Python imports fail in tests
- Run tests from the repo root with the `pytest.ini` project config in place.
- If needed, verify `backend` is on the Python path.
