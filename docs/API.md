# Local command API

`POST /api/command` accepts `{"prompt":"..."}` and streams SSE. No task persistence or conversational context is currently stored.

- `status`: `{stage, message}` for planning, tool_running, streaming.
- `plan`: `{steps: string[]}` after full-plan preflight.
- `step`: `{index: number, state: "running" | "accepted" | "failed"}`; zero-based index.
- `clarification`: `{text}`; terminal, no actions executed. Submit a new complete prompt with the requested details.
- `delta`: `{text}` for informational model responses.
- `final`: `{text, tool?: object[]}`; terminal. A tool result means launch accepted, not page contents verified.
- `error`: `{message, code?, completed?}`; terminal. `partial_execution` disables whole-task retry because some launches may already have happened. Unrun steps are not attempted.

Cancel by aborting the HTTP stream. Pending planner work is cancelled and remaining steps are skipped, but an accepted/in-flight OS launch cannot be undone. The planner has a 60-second deadline and at most one schema-repair attempt.

`GET /health` returns `{"status":"ok","service":"wingent"}`.
