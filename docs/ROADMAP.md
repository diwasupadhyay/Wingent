# Roadmap

## October 2026 update
- M2.5 desktop shell now includes the adaptive overlay, tray lifecycle, taskbar exclusion, and Ctrl+Space.
- M2.6 packaged runtime is complete for a reproducible PyInstaller backend sidecar and app-owned startup.
- Next: explicit confirmation request/response UI, then optional launch-at-login after daily-use validation.
- Deterministic routing now rejects incomplete action plans without performing a partial launch. Optional two-tier local model routing is in place.

## Status snapshot
- M0 — foundation: complete for repository setup, config, dependency checks, and project docs.
- M1 — local command bar: complete and validated with a local backend and streaming frontend.
- M2 — tool system: complete for the initial safe tool set, permission enforcement, and deterministic routing.
- M2.5 — desktop shell: complete for the native Tauri window, Ctrl+Space shortcut, and close-to-hide behavior.
- M3+ — deferred until the stable tool and command flow is proven under real usage.

## Near-term milestones
1. Add a tray menu and startup option after validating the background-app workflow.
2. Add an explicit confirmation UI and backend request model for consequential tools.
3. Expand browser/desktop tools only after the safe command loop is reliable under real usage.
