# Security

## Safety principles
- The app never executes arbitrary shell commands by default.
- Model access remains local-first and does not silently upload private data.
- Sensitive actions are deferred until explicit permission flows are added.
- The deterministic parser never partially executes a multi-step request when any step is unsupported.
- Text model responses are instructed not to claim access to applications, email, files, or screen state.

## Data handling
- Keep environment secrets in `.env` only locally and never commit them.
- Do not log passwords, tokens, or browser content into project files.
- Treat screenshots, browser state, and file contents as sensitive data.

## Current scope
- Model output is untrusted. Strict Pydantic schemas prohibit unknown actions/extra fields and enforce eight steps maximum; the registry rechecks parameters and permissions. A model cannot set confirmation flags.
- Every plan is preflighted before side effects. Runtime failures can still leave earlier launches accepted; they are reported, not rolled back or automatically repeated.
- Folder launching is limited to existing local directories, with explicit paths grounded in the request; network paths and files are rejected. Known folder resolution uses Windows user-shell-folder settings.
- The model can misunderstand intent despite schema validation. The live evaluation corpus is a regression check, not a proof of semantic accuracy.
- Current tools launch approved applications, HTTP(S) URLs, and folders. They do not read page contents, email, or local files.
- Tooling for destructive file operations and browser automation remains deliberately deferred.
