# Self-operating computer reference review

Reviewed 2026-10-04; original changes to Wingent, not imported implementations.

## Sources inspected

- [Self-Operating Computer](https://github.com/othersideai/self-operating-computer), commit `fac568eea7da5e24f8bc91bfc1211b65679177eb`: `operate/operate.py`, `operate/models/apis.py`, `operate/models/prompts.py`, `operate/utils/operating_system.py`, `operate/utils/screenshot.py`.
- [Open-Interface](https://github.com/AmberSahdev/Open-Interface), commit `5a4f706223507fc9d9eb2239cced85385fcb1308`: `app/core.py`, `app/interpreter.py`, `app/llm.py`, `app/models/model.py`, `app/models/gpt4o.py`, `app/models/gpt5.py`, `app/utils/screen.py`.

Read-only clones are in ignored `references/`; no reference code was executed, modified, committed or bundled.

## Actual control loops and tradeoffs

Self-Operating Computer captures the screen before asking a multimodal model for structured operations. Its operating-system adapter interprets normalized click coordinates, typing and hotkeys. Conversation history carries the objective and previous decisions. The main loop stops on model `done` or its iteration bound. Some adapter errors are printed rather than propagated, and model completion is not an independent task oracle.

Open-Interface separates UI/status queues, model requests and a PyAutoGUI interpreter. Its core executes a model-produced step list, then asks again using the original objective and incremented step number unless `done` is populated. Screenshot handling and provider behavior differ: GPT4o uploads images into a thread, while GPT5 sends the current image and objective. The interpreter dynamically exposes PyAutoGUI methods and runs a platform-specific warm-up key before actions. Neither arbitrary dynamic dispatch nor blind multi-action batches are appropriate for Wingent's approval/freshness boundary.

## Concepts adopted in Wingent v24

- One computer action/observation vocabulary. The production registry no longer mixes legacy desktop IDs with computer frame IDs. Legacy modules remain only for compatibility tests.
- Keep original goal, working context and current pixels in the model brain. Structured app tools remain accelerators, not a boundary on possible environments.
- Explicit task-long `desktop` scope supports switching observed windows and following new foreground dialogs. Default `window` scope remains narrower. Each input still targets the current window/frame; no blind global input.
- Observe after each action, including foreground transitions. Never silently refocus the old window after it opens a dialog.
- Empty installed-app discovery falls back to observing running windows, not premature termination.
- UIA exposes supported actions and bounded TextPattern text; non-actionable targets return known-no-effect so the model can use visual clicking instead.
- Preserve strict schemas, local-only image transport, cancellation, process identity, one-use frames, exact sensitive-action approvals and honest unverified completion.
- Bounded hover/wait and same-window approved drag add general gestures without exposing arbitrary Python methods. Drag cancellation releases the mouse button.

Additional inspected source: Open-Interface's `app/resources/context.txt` and Self-Operating Computer's Ollama path in `operate/models/apis.py`. Open-Interface prompts for short batches and screenshots after navigation, checks the intended typing target, and requests manual login. Its core retries malformed JSON once, then recursively continues until the model reports done; interruption is checked between steps. Self-Operating Computer removes old Ollama image references from history to avoid repeatedly processing them, but its error path recursively retries. Wingent keeps only the current image, bounded repair/recovery budgets and host-owned approval/completion rules. Neither reference establishes safe universal competence simply by looping.

## Not claimed

No reference project's model `done` output is adopted as trusted proof. This release does not establish arbitrary-app competence, secure-desktop access, unattended consequential actions, or a universal task verifier. Native input checks and autonomous model evaluations are reported separately in `COMPUTER_OPERATOR.md`.
