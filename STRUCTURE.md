# Wingent structure

Current runtime: `wingent-desktop-v3` (2026-10-08).

| Path | Responsibility |
| --- | --- |
| `backend/app/main.py` | FastAPI/SSE, provider settings and task entry |
| `backend/app/self_operating.py` | Screenshot/action loop, schemas, batching, recovery and cancellation |
| `backend/app/task_brain.py` | Goal outcomes, launch memory, Windows shortcut contracts and visual completion review |
| `backend/app/llm.py`, `provider_settings.py`, `model_routing.py` | Local/cloud models and configuration |
| `backend/app/approvals.py` | Expiring action-bound approvals |
| `backend/app/unicode_input.py` | Native Unicode input helper |
| `backend/vendor/self_operating_computer/` | Licensed source; adapted prompts and PyAutoGUI driver are active |
| `src/App.tsx`, `src/styles.css` | Overlay, settings, progress, review and Stop |
| `src-tauri/src/lib.rs` | Tray, shortcut, window lifecycle and owned backend |
| `backend/sidecar.py`, `scripts/build-*.ps1` | Backend freezing and release packaging |
| `backend/tests/`, `src/App.test.tsx` | Regression tests; Rust tests are in lib.rs |
| `scripts/evaluate-computer.py`, `scripts/evaluate-task.py` | Opt-in live evaluations |
| `scripts/diagnose-vision.py` | Vision diagnostics |
| `references/` | Ignored, unchanged source checkouts for study |

Generated `.build/`, `dist/`, `node_modules/` and `src-tauri/target/` are not documentation sources. This cleanup does not remove them.

## Documentation

- [README](README.md): setup/build and current limits.
- [Memory](MEMORY.md): compact development handoff.
- [Implementation plan](docs/SELF_OPERATING_AGENT_PLAN.md): sole phase/status tracker.
- [Reference study](docs/REFERENCE_AGENT_STUDY.md): source analysis; Wingent comparison explicitly historical.
- [Security](docs/SECURITY.md): current protections and gaps.

Upstream README/license/adaptation files remain for attribution and source context. Obsolete plans, architecture and evaluations of the removed runtime are recoverable from Git.
