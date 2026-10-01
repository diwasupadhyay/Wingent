# Local command API

`POST /api/command` accepts `{"prompt":"..."}` and streams SSE. No task persistence or conversational context is currently stored.

- `status`: `{stage, message}` for planning, tool_running, streaming.
- `plan`: `{steps: string[]}` after full-plan preflight.
- `task`: `{task_id, goal, criteria}` identifies a request-local runtime task; there is no resume endpoint yet.
- `action`: `{task_id, index, label}` updates/adds a step selected from current observations.
- `step`: `{index: number, state: "running" | "accepted" | "failed" | "unknown"}`; zero-based index. Unknown is not a safe-to-retry failure.
- `clarification`: `{text}`; terminal, no actions executed. Submit a new complete prompt with the requested details.
- `delta`: `{text}` for informational model responses.
- `final`: `{text, task_id?, outcome?, verified?, evidence?, completed?, attempted?, tool?}`; terminal. Runtime outcomes distinguish `completed` from `unverified`; informational responses have no runtime outcome. Existing launches always return `unverified`, `verified: false`.
- `error`: `{message, code?, completed?}`; terminal. `partial_execution` disables whole-task retry because some launches may already have happened. Unrun steps are not attempted.

Cancel by aborting the HTTP stream. Pending planner work is cancelled and remaining steps are skipped, but an accepted/in-flight OS launch cannot be undone. The planner has a 60-second deadline and at most one schema-repair attempt.

Runtime `status.stage` adds observing, executing, verifying, recovering, and awaiting_input. The UI maps executing to its tool-running animation. Runtime clarification may follow earlier actions; it must not imply no effects unless no dispatch occurred.

`GET /health` returns `{"status":"ok","service":"wingent","runtime":"observation-loop-v1"}`. Use the runtime marker to confirm a rebuilt sidecar is running rather than a stale binary.
