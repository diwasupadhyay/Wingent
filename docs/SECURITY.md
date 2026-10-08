# Current safety boundaries

Updated: 2026-10-08; applies to `wingent-desktop-v3`, not the removed tool-registry runtime.

Wingent sends real input with the user's desktop privileges. It is not a sandbox. Use non-sensitive test windows while reliability work is incomplete.

## Implemented

- Typed action parsing, bounded batches/rounds, single-task input ownership and repeat guards.
- Windows shortcut/declared-target validation and re-observation after navigation. These are correctness checks, not comprehensive semantic authorization.
- Stop/disconnect cancellation checks; PyAutoGUI screen-corner fail-safe; held-key release on interruption. Cancellation cannot undo effects.
- Review mode approves each input action. Otherwise approval depends on the model setting `requires_confirmation`; approval records are action-bound, expiring and single-use.
- Local Ollama by default. Cloud configuration is explicit and screenshots require opt-in. Keys are session-only. Cloud text/images leave the PC and may incur charges.
- Tauri checks its owned backend runtime/instance on a private loopback port.

## Important gaps

- Model-sensitive-action classification can miss consequential clicks or typing. There is no comprehensive host-enforced semantic policy; normal mode is not guaranteed safe for unattended use.
- The driver checks captured foreground-window identity and geometry before input, but lacks UIA field-level targeting and comprehensive occlusion checks. A stable window is not proof that the correct field is focused.
- Screenshots may contain personal information; reliable password/private-content redaction is absent.
- Screen text can contain malicious instructions. Prompt warnings alone are not a complete defense.
- Completion review is model-based. `verified:false` must not be presented as independently proven success.
- Secure desktop/UAC, elevation, crash-safe continuation and broad multi-monitor support are not established.

The [plan](SELF_OPERATING_AGENT_PLAN.md) schedules host preconditions, risk checks, evidence-based completion and cancellation tests. Ordinary navigation should stay low-friction; destructive changes, sending, purchases, installation and executable commands need meaningful confirmation. Do not remove safeguards to improve demo success rates.
