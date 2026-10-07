# Source and adaptations

Copied from OthersideAI/self-operating-computer at commit
`fac568eea7da5e24f8bc91bfc1211b65679177eb`, under the included MIT license.
All 33 upstream tracked files are included; `.git` and local secrets are excluded.
The separate `references/` checkout remains unchanged.

Wingent uses the adapted `operate/utils/operating_system.py` input driver.
Its active Windows prompt is in `app/self_operating.py`; upstream prompts remain
as reference source, not concatenated into the production instruction contract.
The Windows input driver uses the same PyAutoGUI movement, clicks and hotkeys,
with Unicode typing, cancellation, propagated failures and in-memory screenshots.
The upstream decorative cursor circle is omitted to reduce click latency.

`app/self_operating.py` adapts the upstream action-batch loop to streamed UI events
and Wingent's existing local/cloud providers. It bypasses the former tool planner,
window grants, UIA discovery and per-action model round trips. Each batch is followed
by a new screenshot. Completion is explicitly a model visual assessment.

Upstream CLI, voice, OCR, SoM, and legacy SDK integrations are preserved as source;
they are **not enabled in Wingent's command bar**. Their old pinned requirements
are not installed by Wingent's build. The command bar uses direct vision coordinates.
The active driver targets the primary monitor, as upstream PyAutoGUI does.

Rollback point before the replacement: `e7f5645`.

Validation on Windows, 2026-10-07: the isolated fixture passed native movement,
clicking, typing and hotkeys. The real local `qwen3-vl:4b-instruct` loop also passed
the fixture: screenshot, field click, text entry, Confirm click, fresh screenshot,
completion. The fixture checked both the input and submitted text independently.
Earlier constrained-grammar runs failed; the active operator now uses upstream-style
JSON prompting with host validation. This is evidence for this fixture, not all apps.
