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
window grants and per-action model round trips. Each batch is followed
by a new screenshot. Completion is explicitly a model visual assessment.

Upstream CLI, voice, OCR, SoM, and legacy SDK integrations are preserved as source;
they are **not enabled in Wingent's command bar**. Their old pinned requirements
are not installed by Wingent's build. The command bar uses vision coordinates and
bounded, read-only Windows accessibility targets with frame-local IDs. Clicking a
target still moves the real pointer; it does not invoke application-specific scripts.
The active driver defaults to foreground cropping, with explicit full-primary-screen
overview available. It draws numbered accessible targets in model images, rechecks
their identity/name/bounds before clicks, and reobserves after every click.
It maps normalized image coordinates back to the
captured physical region and rejects changed foreground/geometry before input.

Rollback point before the replacement: `e7f5645`.

Validation on Windows, 2026-10-07: the isolated fixture passed native movement,
clicking, typing and hotkeys. The real local `qwen3-vl:4b-instruct` loop also passed
the fixture: screenshot, field click, text entry, Confirm click, fresh screenshot,
completion. The fixture checked both the input and submitted text independently.
Earlier constrained-grammar runs failed; the active operator now uses upstream-style
JSON prompting with host validation. This is evidence for this fixture, not all apps.
