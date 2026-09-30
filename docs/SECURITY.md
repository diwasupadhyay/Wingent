# Security

## Safety principles
- The app never executes arbitrary shell commands by default.
- Model access remains local-first and does not silently upload private data.
- Sensitive actions are deferred until explicit permission flows are added.

## Data handling
- Keep environment secrets in `.env` only locally and never commit them.
- Do not log passwords, tokens, or browser content into project files.
- Treat screenshots, browser state, and file contents as sensitive data.

## Current scope
- The current build is intentionally limited to safe local prompt handling and streaming responses.
- Tooling for destructive file operations and browser automation remains deliberately deferred.
