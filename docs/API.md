# Local command API

`POST /api/command` accepts `{"prompt":"...","review_actions":false}` and streams SSE. Review mode asks before every action, even safe ones. Consequential tool permissions always require approval regardless of review mode. No task persistence or conversational context is currently stored.

- `status`: `{stage, message}` for planning, tool_running, streaming.
- `plan`: `{steps: string[]}` after full-plan preflight.
- `task`: `{task_id, goal, criteria}` identifies a request-local runtime task; there is no resume endpoint yet.
- `action`: `{task_id, index, label}` updates/adds a step selected from current observations.
- `confirmation_required`: `{approval_id, token, task_id, tool, arguments, expires_in, message}` pauses before dispatch. Show the exact tool/arguments; do not log or display the token. Default approval expiry is 60 seconds, also bounded by the task deadline.
- `step`: `{index: number, state: "running" | "accepted" | "failed" | "unknown"}`; zero-based index. Unknown is not a safe-to-retry failure.
- `clarification`: `{text, attempted?, completed?}`; terminal, may follow earlier actions. Submit a new complete prompt with the requested details; check partial results before resubmission.
- `delta`: `{text}` for informational model responses.
- `final`: `{text, task_id?, outcome?, verified?, evidence?, completed?, attempted?, tool?}`; terminal. Runtime outcomes distinguish `completed` from `unverified`. A model finish/answer cannot grant verified status; current built-in tools cannot independently verify arbitrary goals. Artifact read-back checks appear in tool results, not as whole-goal verification.
- `error`: `{message, code?, completed?}`; terminal. `partial_execution` disables whole-task retry because some launches may already have happened. Unrun steps are not attempted.

Cancel by aborting the HTTP stream. Pending planner work is cancelled and remaining steps are skipped, but an accepted/in-flight OS launch cannot be undone. The planner has a 60-second deadline and at most one schema-repair attempt.

Runtime `status.stage` adds observing, executing, verifying, recovering, and awaiting_input. The UI maps executing to its tool-running animation. Runtime clarification may follow earlier actions; it must not imply no effects unless no dispatch occurred.

`POST /api/approvals/{approval_id}` accepts `{"token":"<stream token>","approve":true}` or false. Only a strict boolean is accepted. Returns 200 when the response is recorded, 409 for invalid/expired/already-answered requests, or 422 for invalid input. This endpoint does not dispatch a tool itself. Approval is consumed once at execution, after revalidation. Closing the task stream revokes its outstanding approvals.

`GET /api/capabilities` returns tool input/output schemas, permissions, timeouts, cancellation/retry metadata, observer/verifier availability, and capability guidance. It never includes pending approvals, tokens, or executor functions.

`GET /health` returns `{"status":"ok","service":"wingent","runtime":"operator-v3"}`. Use the runtime marker to confirm a rebuilt sidecar is running rather than a stale binary.

Natural tasks now use next-tool selection followed by typed argument generation, then repeat from observed results. They do not emit an initial full plan. Default API limits: 12 total model calls (including argument generation/repair), 180 seconds total, 16 actions. `/api/capabilities` also includes `loaded_skills`. Legacy `plan`/`delta` events remain protocol-compatible but are not required by this path.
