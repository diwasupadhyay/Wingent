# Local command API

`POST /api/command` accepts `{"prompt":"...","review_actions":false}` and streams SSE. A genuine model clarification can be answered with `{"prompt":"answer","resume_task_id":"<id>"}`. Review mode asks before every action, even safe ones. Consequential tool permissions always require approval regardless of review mode. Clarification state is held only in this backend process for 15 minutes (at most 16 tasks), consumed once, and is not durable.

- `status`: `{stage, message}` for planning, tool_running, streaming.
- `plan`: `{steps: string[]}` after full-plan preflight.
- `task`: `{task_id, goal, criteria}` identifies a runtime task, including one continued after clarification.
- `action`: `{task_id, index, label}` updates/adds a step selected from current observations.
- `confirmation_required`: `{approval_id, token, task_id, tool, arguments, expires_in, message}` pauses before dispatch. Show the exact tool/arguments; do not log or display the token. Default approval expiry is 60 seconds, also bounded by the task deadline.
- `step`: `{index: number, state: "running" | "accepted" | "failed" | "unknown"}`; zero-based index. Unknown is not a safe-to-retry failure.
- `clarification`: `{text, attempted?, completed?, resume_task_id?}`; terminal, may follow earlier actions. Only a genuine model question includes `resume_task_id`. Answer that question using the continuation request; other clarification/denial results are not resumable. Earlier effects are retained and not dispatched again by the continuation.
- `delta`: `{text}` for informational model responses.
- `final`: `{text, task_id?, outcome?, verified?, evidence?, completed?, attempted?, tool?}`; terminal. Runtime outcomes distinguish `completed` from `unverified`. A model finish/answer cannot grant verified status; current built-in tools cannot independently verify arbitrary goals. Artifact read-back checks appear in tool results, not as whole-goal verification.
- `error`: `{message, code?, completed?}`; terminal. `partial_execution` disables whole-task retry because some launches may already have happened. Unrun steps are not attempted.

Cancel by aborting the HTTP stream. Pending asynchronous reasoning work is cancelled and remaining actions are skipped, but an accepted/in-flight synchronous effect cannot be undone. The runtime applies operation/tool deadlines as well as the overall task budget; schema repair also consumes model calls. This is not a full-plan execution guarantee.

Runtime `status.stage` adds observing, executing, verifying, recovering, and awaiting_input. The UI maps executing to its tool-running animation. Runtime clarification may follow earlier actions; it must not imply no effects unless no dispatch occurred.

`POST /api/approvals/{approval_id}` accepts `{"token":"<stream token>","approve":true}` or false. Only a strict boolean is accepted. Returns 200 when the response is recorded, 409 for invalid/expired/already-answered requests, or 422 for invalid input. This endpoint does not dispatch a tool itself. Approval is consumed once at execution, after revalidation. Closing the task stream revokes its outstanding approvals.

Resume requests return HTTP 409 for an expired/used continuation ID and HTTP 503 when Ollama is unavailable (the pending ID is retained in that case). A network interruption after a resume request is accepted can still lose the in-memory continuation; no durable checkpoint or unknown-effect reconciliation is implemented yet. At most three genuine clarifications are allowed per task.

`GET /api/capabilities` returns tool input/output schemas, permissions, timeouts, cancellation/retry metadata, observer/verifier availability, and capability guidance. It never includes pending approvals, tokens, or executor functions.

Experimental browser tools are `browser_search`, `browser_open`, `browser_inspect`, `browser_follow_link` (latest observed index only), and `browser_play_media` (returns `ok: true` only when media time advances). They operate a separate agent-owned Chrome profile. The current restricted-session live probe lost the debugger connection before observing a page; these tools are **not yet validated for real playback**.
If controlled Chrome crashes, search/open tries a normal Chrome window and reports `new_window_visible` separately from `page_observed`; no newly visible window yields `effect: unknown`. `observe_windows` lists bounded visible top-level process names/titles for read-only checking. Neither a visible window nor a launched URL proves page or media state. Operator-selected URLs and link indices must come from the user or a live browser observation; invented video IDs are rejected before dispatch.

`GET /health` returns `{status,service,runtime,instance_id}`. Current source runtime is `operator-v24`. Tauri starts a private per-run loopback port and requires both the matching runtime and its own instance ID. The overlay obtains that port from Tauri; it does not adopt a port-8000 listener. Unknown listeners are never killed.

Production GUI tools use one computer session. `computer_begin` accepts an observed `window_id`, purpose and optional `scope` (`window` default, or explicitly approved `desktop`). `computer_observe` accepts an optional observed window ID; omission follows the foreground. `computer_action` takes a one-use `frame_id` and typed click/type/hotkey/scroll/invoke/hover/wait arguments. Drag uses `x,y,end_x,end_y` and always requires `computer_confirm_action`; hover/drag/wait duration is bounded to 100..2000 milliseconds. A desktop grant ends with the task and does not waive exact sensitive-action approval.

`GET /api/model-status` checks the selected default local model through Ollama's model catalogue and returns `{ready,code,message,model}`. The overlay uses this status instead of treating an open TCP port as model readiness. Command preflight retries a transient timeout once, then reports a specific `ollama_timeout`, `ollama_unreachable`, `ollama_model_missing`, `ollama_http_error` or `ollama_invalid_response` error. A resumed task returns the diagnostic in HTTP 503 without consuming its pending continuation.

Operator terminal events include `progress`: `plan_unverified` contains bounded model notes (outcomes, constraints, targets, remaining work and referenced record IDs); `action_history` contains host-recorded statuses and provenance; `source_coverage` reports contiguous pages of each last-observed file version. None grants verified completion. `task_read_result` is available only inside the current task's operator registry and retrieves historical results without repeating external actions.

Natural tasks now propose one next tool and its typed arguments in a single model response. Invalid or missing arguments use the selected tool's typed repair path. The operator does not emit an initial full script; it replans after observed outcomes. Default API limits: 12 total model calls (including repairs), 180 seconds total, 16 actions. `/api/capabilities` also includes `loaded_skills`. Legacy `plan`/`delta` events remain protocol-compatible but are not required by this path.
