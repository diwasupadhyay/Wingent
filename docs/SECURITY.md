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
- Phase 2 removes boolean auto-approval. Requests bind task, exact normalized arguments, tool name and revision; a one-use token is returned only to the requesting task stream. Approve/deny is an explicit frontend response. Restricted tools cannot be approved.
- Approvals expire after 60 seconds (or sooner at the task deadline), cannot be replayed, and are revoked on stream closure. After approval the runtime observes/revalidates again. Any changed canonical arguments fail the consumption check.
- Capability guidance is trusted application knowledge only, not executable code or permission authority. Model plans are validated against schemas generated from the registered tools; permission/approval fields are not legal model arguments.
- Review mode lets users require approvals for ordinary safe launches. The shipped tools remain launch/search/folder tools; consequential-tool contract tests use controlled fixtures, not real destructive actions.
- Scope limitation: an approval binds argument values, not immutable filesystem handles. Future file mutation tools must address filesystem races and target identity in their preconditions/execution design. Local approval tokens are not a defense against a malicious process already controlling the user's session.
- Phase 1 runtime separates accepted, no-effect, and unknown action outcomes. Only trusted adapters may guarantee no effect; arbitrary exceptions after dispatch are unknown. Unknown effects stop further dispatch and suppress whole-task retry.
- A planner's finish decision cannot claim success. Completion requires trusted verifier evidence covering all goal criteria from the latest observation and current action count, within the freshness window.
- Existing launch adapters cannot verify window/page state and never produce completion evidence. Generic verified/recovery tests use controlled adapters only.
- Model output is untrusted. Strict Pydantic schemas prohibit unknown actions/extra fields and enforce eight steps maximum; the registry rechecks parameters and permissions. A model cannot set confirmation flags.
- Every plan is preflighted before side effects. Runtime failures can still leave earlier launches accepted; they are reported, not rolled back or automatically repeated.
- Folder launching is limited to existing local directories, with explicit paths grounded in the request; network paths and files are rejected. Known folder resolution uses Windows user-shell-folder settings.
- The model can misunderstand intent despite schema validation. The live evaluation corpus is a regression check, not a proof of semantic accuracy.
- Current tools launch approved applications, HTTP(S) URLs, and folders. They do not read page contents, email, or local files.
- Tooling for destructive file operations and browser automation remains deliberately deferred.
# General operator boundaries (2026-10-02)

Natural-language tool selection does not grant authority. Every file operation currently requires approval for the exact canonical path and arguments. Creation uses exclusive mode (no overwrite); listing is nonrecursive and reads are bounded UTF-8 pages. Links/junctions, remote/device paths, alternate streams and reserved names are rejected. Path revalidation is defense in depth, **not** a handle-based sandbox against hostile concurrent filesystem changes; untrusted concurrent mutation remains a hardening item.

Opt-in Python skills execute as trusted native backend code; metadata and staging checks cannot sandbox malicious extension code. Models cannot enable, download or import skills. No terminal, installer, security-setting modification, browser-session takeover or coordinate-input tool is added by this slice.
