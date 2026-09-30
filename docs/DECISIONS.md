# Decisions

## Local-first model default
We default to Ollama to avoid network dependencies and keep the app local-first.

## Streaming before full chat history
The first version streams partial outputs to the UI for a faster perceived response and better cancellation UX.

## Minimal but structured state
The app keeps a clear status and message lifecycle instead of relying on loose chat history.

## No speculative automation yet
Browser automation, desktop control, and voice are intentionally deferred until the command bar and backend loop are proven.
