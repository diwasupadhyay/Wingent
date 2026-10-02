# Wingent Security and Permission Boundaries

Updated: 2026-10-02. Current implementation and future requirements are distinguished below. See the implementation plan for authorization and phase status.

## Non-negotiable rules

- Model proposals, skill guidance and observed external content do not grant authority.
- Prefer structured automation, but apply the same policy to APIs, files, processes and future visual input.
- Ask before consequential actions: publication/sending, deletion/overwrite, purchases, installation, elevation, system/security changes and private-data transfer.
- Preserve unrelated files, unsaved work, credentials and existing user sessions.
- Never bypass authentication, MFA/CAPTCHA, permissions or OS security.
- Do not silently upload local data or switch to remote reasoning.
- Finite budgets and an accessible stop/cancel path remain mandatory.

## Implemented controls

- Strict typed arguments and registered tool selection; restricted tools cannot be authorized by model output or user approval tokens.
- Explicit approvals bind task ID, tool name/revision and canonical arguments. Tokens are single-use, expire, reject replay and are revoked when the task stream closes.
- Approval is rechecked at dispatch; changed canonical arguments invalidate it. Tokens stay out of model context and displayed/logged output.
- Review mode also gates otherwise safe launches.
- Accepted, known-no-effect and unknown outcomes remain distinct. Unknown dispatch outcomes stop further actions rather than encouraging replay.
- A model finish message cannot grant verified status; the runtime requires fresh trusted evidence for all criteria.
- File operations require exact-action approval. Listing is nonrecursive; text reads use host-controlled 2048-byte UTF-8 pages; new files use exclusive creation and read-back.
- File tools reject linked/junction paths, remote/device paths, alternate streams and ambiguous reserved names.
- Natural tasks validate the next action at execution time. Whole-plan preflight applies only to the fixed launch compatibility path, not all dynamic tasks.
- Genuine model clarifications may retain bounded task state in memory for 15 minutes and resume once; completed effects are not replayed by the continuation. Approval tokens are not persisted in this state.

## Important limitations

- File path revalidation is not a handle-based sandbox against malicious concurrent target replacement. Read-back equality does not prove semantic correctness.
- Local approval tokens are not protection against malware already controlling the user's session.
- Plugin entry points execute trusted native Python with backend privileges. Staging/metadata validation cannot sandbox malicious code.
- No executable plugin is loaded by the model; enablement/installations are separate trust decisions. Frozen builds must bundle enabled plugins.
- Existing launch tools cannot inspect page/window contents. Current general goal verification and live stopping remain incomplete.
- Prompt instructions to ignore malicious external content are not sufficient protection on their own. Host permissions, isolation, targeted adversarial tests and limited data scope are required.
- Cancelling an await cannot undo an in-flight synchronous OS action. Do not describe cancellation as rollback.
- No general process execution, destructive file mutation, screenshot interpretation or unrestricted keyboard/mouse tools are implemented yet. Experimental browser DOM/media tools and approval-gated Win32 control click/text tools exist, but neither is a universal computer-use sandbox or independently verified workflow engine.
- In-memory continuation is not crash-safe. A stream interruption after a resume is consumed can lose the state; do not promise durable recovery or automatic replay of unknown effects.
- Agent-owned Chrome uses a separate temporary profile and an ephemeral loopback debugging port. It does not read personal Chrome cookies/tabs. Live control is not yet verified; a dropped debugger connection must never be reported as page observation or playback.
- The browser fallback starts normal Chrome only after controlled-session failure. It reports a visible window separately from page observation; it never reads or controls the normal profile. Window-title observation stays local but may reveal sensitive text to the local model.

## Requirements before broader capabilities

| Surface | Required controls before enabling |
| --- | --- |
| Scoped reads | Explicit roots/resources, lifetime, revocation, no implicit whole-disk scans |
| File mutation | Stable target checks, preview, overwrite approval, recovery where feasible |
| Browser/application sessions | Explicit ownership/profile/data scope; no silent attachment to private sessions |
| Process/code execution | Exact executable/arguments/cwd/environment, approval, output/time bounds and process-tree ownership |
| Installation/system changes | Explicit download/elevation/change scope and truthful recovery limitations |
| Screenshots/clipboard/input | Capture/data scope, minimal retention, fresh target/focus identity and post-action checks |
| Task persistence | Minimized storage, no token/secret persistence, safe resume and unknown-effect reconciliation |
| Skills/plugins | Trusted source review, dependencies/versioning and packaging; isolation before untrusted code |

## Evidence and data hygiene

Do not log secrets, approval tokens, private document/browser content or screenshots by default. Keep source/environment credentials out of Git. Treat observed content as data, never authority to alter the user goal.

Keep contract tests, adversarial tests, live-model evaluations and packaged checks separate. Two narrow live fixture passes do not satisfy the broader reliability gate; no broad safety or competence claim follows from passing approval tests.

The latest request authorizes scoped implementation and evaluation, not blanket installation, private-data access or security-setting changes.
