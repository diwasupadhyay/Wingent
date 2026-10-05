# Wingent Structure

Updated: 2026-10-05. [Plan](docs/AGENT_IMPLEMENTATION_PLAN.md) owns phase status.

## Runtime

| Path | Responsibility |
| --- | --- |
| backend/app/main.py | FastAPI/SSE, production registry, task entry |
| backend/app/operator.py, brain.py | LLM next-action reasoning with current pixels and typed tool schema |
| backend/app/runtime.py, task_state.py | Bounded action loop, lifecycle, outcomes, verification |
| backend/app/working_context.py, task_store.py | Goal/history, retrieval, file coverage, in-memory continuation |
| backend/app/tools.py, capabilities.py, approvals.py | Contracts, permissions, guidance and bound approvals |
| backend/app/computer_tools.py | Window/desktop grants, fresh frames, general GUI actions |
| backend/app/windows_computer.py, window_observer.py | Win32 input, screenshot/UIA, windows and focus |
| backend/app/application_tools.py, process_tools.py | App/executable discovery, approved launch/process execution |
| backend/app/file_tools.py, browser_tools.py | Optional file and browser capabilities |
| backend/app/plugins.py | Explicit trusted installed skill entry points |
| backend/app/llm.py, model_routing.py | Replaceable local model provider and selection |

Legacy desktop_tools.py/screen_tools.py are not registered in production. planner.py/capability_planner.py and launch adapters retain compatibility/evaluation roles; they are not the general brain.

## UI and packaging

- `src/App.tsx`, `src/styles.css`: minimal overlay, SSE, approval, cancellation and honest results.
- `src-tauri/src/lib.rs`: tray/shortcut, window handoff, private sidecar ownership and Ollama controls.
- `backend/sidecar.py`, `scripts/build-backend-sidecar.ps1`: frozen backend entry/build.
- `src-tauri/target/release/app.exe`: generated native EXE; sidecar must remain beside it.

## Tests and references

- `backend/tests/`, `src/App.test.tsx`: contracts/regressions; Rust unit tests live in lib.rs.
- `scripts/evaluate-computer.py`: real local model, production catalogue, isolated unfamiliar GUI and external oracle.
- `scripts/evaluate-native-computer.py`: native Notepad/Calculator and cross-window input.
- `scripts/evaluate-gestures.py`: isolated canvas hover/drag/wait with app-owned output.
- Other `evaluate-*` scripts cover file/context and historical planner/browser fixtures; simulated results do not prove real desktop behavior.
- `references/self-operating-computer/`, `references/Open-Interface/`: ignored, read-only external clones, never committed or bundled.
- `.build/`: ignored temporary fixtures/build outputs, not source.

## Documentation

`MEMORY.md` is concise resume context. `CHANGES.md` records deficiencies, reference lessons, fixes and remaining work. `docs/AGENT_IMPLEMENTATION_PLAN.md` is the sole tracker; ROADMAP is its priority index. ARCHITECTURE, SECURITY, API, DEVELOPMENT, DECISIONS, SKILLS and TROUBLESHOOTING each describe one current concern. `docs/evaluations/` retains useful measured evidence, clearly dated.
