# Security and Permission Boundaries

Updated: 2026-10-05. These are implemented boundaries and explicit limitations, not a claim of a secure sandbox.

## Computer grants

Default `computer_begin` scope is one window. Starting a requested task permits routine screenshots/input without a separate initial approval; Review mode still asks for each action. Desktop scope permits task-long operation across observed applications and dialogs. Wingent's overlay is excluded from control targets. Consequential actions retain exact approval.

Frames bind HWND, PID, executable, geometry and capture time. Possible input consumes the frame. Recheck foreground and coarse pixels before dispatch; observe again afterwards. One task owns desktop input at a time. Stop/task end revokes control. A held Escape is checked during dispatch; a brief tap during model reasoning is not a latched global stop. Cancellation cannot undo prior effects.

Enter/Delete/Windows key, multiline text, paste shortcuts, drag and recognized sensitive UIA labels require exact approval. The model must also flag sending, deletion, purchases, installation, terminal execution and other consequential semantics. These mechanical checks are incomplete: a harmless-looking click or shortcut may still have an important effect. This is not a sandbox.

Drag is limited to a visible path inside the approved window and releases the button on interruption. Occlusion/focus changes can leave a partial unknown effect; never replay blindly.

Known UIA password controls block capture. Custom/canvas authentication may not expose them; stop for login/MFA/CAPTCHA rather than bypassing it. Capture can include occluding sensitive windows. Secure/elevated desktop is unsupported.

## Data and model boundary

By default production pixels stay in memory and go only to loopback Ollama. Cloud mode is explicitly selected in Settings; task text/tool results go to the configured HTTPS provider and images require the screenshot-sharing checkbox. Keys are session-only, omitted from API responses and never persisted. No silent cloud fallback or screenshot persistence. Synthetic evaluation screenshots may be saved only in ignored build fixtures. Screen text, files and tool output are untrusted data, never new instructions or authority.

Model proposals cannot grant permissions or certify completion. Typed registered tools, exact target checks and host policy remain authoritative. A model finish or dispatch acknowledgement stays unverified unless fresh trusted evidence covers the goal.

## Approval and execution

Approvals bind task, tool revision and canonical arguments; tokens are single-use and expiring. Revalidate before execution. Tokens are not displayed/logged or retained for resume. Restricted tools cannot become allowed through a model proposal. Review mode also gates safe actions.

Outcomes distinguish accepted, known-no-effect and unknown. Unknown effects stop further dispatch until reconciled; cancellation is not rollback. Finite model/action/time/recovery budgets remain mandatory.

Files require exact-action approval. Existing operations provide nonrecursive listing, host-sized UTF-8 reads and exclusive new-file creation/read-back. They reject links/junctions, remote/device paths and ambiguous names, but path revalidation is not a handle-based adversarial filesystem sandbox. Matching written bytes does not prove semantic correctness.

Native process execution binds executable, arguments, working directory and bounded output/time with approval. Cancellation attempts owned process-tree cleanup; detached descendants and earlier effects are not guaranteed reversible. Native code runs with backend privileges.

## Extensions and sessions

Trusted installed Python skill entry points load only through explicit startup configuration. They are not sandboxed; the model cannot install/import/enable them. Frozen packages must bundle enabled code and metadata.

Browser structured tools use a separate agent-owned profile and do not silently attach to personal cookies/tabs. Their live reliability is distinct from generic desktop control. A desktop grant can visually interact with a selected browser window and must respect the same data/sensitive-action boundary.

Clarification continuation is in-memory, expiring and single-use, not crash-safe. Interrupted resume or in-flight unknown effects require reconciliation before replay.

Tauri owns a per-run backend port and checks runtime/instance identity. Local approval tokens do not protect against malware already controlling the user's session.

## Evaluation and development

Only newly owned windows and isolated files may be auto-approved by test harnesses. Never use broad automatic approval to obtain a passing test. Keep reference clones under ignored `references/` and unchanged; they are not executable dependencies. Record native, model and packaged results separately.

Personal-data scope, downloads, executable skill installation, elevation and consequential system changes require a deliberate decision. Passing a finite evaluation suite is not proof of universal safety.
