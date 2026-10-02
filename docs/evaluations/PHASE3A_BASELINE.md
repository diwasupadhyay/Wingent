# Phase 3A local-model baseline

Updated: 2026-10-03. Source fixture: `scripts/evaluate-phase3a.py`.

This is an isolated reasoning regression corpus, **not** a proof of real PC control. It uses a temporary inert `NoteSpace.exe`, a fake launcher, and only the registered `application_search`/`application_open` tool contracts. Exact-action approval is granted only for that inert fixture. Nothing from the user's installed apps is launched. All cases require honest, unverified completion or a clarification; no model output counts as independent verification.

Run with `python scripts/evaluate-phase3a.py --variant both`. The script prints one JSON record per case, including model, elapsed seconds, model-call count, actions, outcomes, terminal event and failure class. The corpus and classifications are fixed in source. The focused variant adds app-tool guidance to the default system prompt, with the same cases and model.

| Case | Expected behavior |
| --- | --- |
| locate | Search for a named installed app, report the observed path, do not launch |
| launch | Search for a named app, request exact approval, launch once, report visibility unverified |
| missing | Search for a missing app and report it absent, without substitution |
| ambiguous | Ask which app, without guessing or launching |

Installed model/configuration: `llama3.2:3b`, Ollama `0.34.4`, structured generation at temperature 0, `num_predict=1200`, `num_ctx=8192`; task limits 12 model calls / 180 seconds. Local GPU: RTX 3050 Laptop, 4 GiB VRAM; physical RAM approximately 19.7 GiB. All fixture results are local. No alternative model was downloaded or evaluated.

## Recorded result after host grounding changes

| Variant | Case | Seconds | Calls | Recorded actions | Terminal | Failure class |
| --- | --- | ---: | ---: | --- | --- | --- |
| Default | locate | 10.80 | 6 | search | unverified final | none |
| Default | launch | 6.47 | 4 | none | unverified final | planning |
| Default | missing | 5.91 | 4 | none | unverified final | planning |
| Default | ambiguous | 6.12 | 4 | none | unverified final | termination |
| Focused | locate | 11.59 | 6 | search | unverified final | none |
| Focused | launch | 6.11 | 4 | none | unverified final | planning |
| Focused | missing | 6.00 | 4 | none | unverified final | planning |
| Focused | ambiguous | 6.23 | 4 | none | unverified final | termination |

Both variants passed 1/4, and neither launched the named app. This small corpus identifies a model/planning and premature-stopping problem, not a demonstrated benefit from extra guidance. The exact times and outputs may vary across runs. Earlier runs, before host checks, proposed ungrounded paths and even repeated a launch through a new discovery ID; host path binding, observed-ID validation and same-executable deduplication now prevent those requests from reaching approval/dispatch. A model may still fail to choose a useful action at all.

Failure categories: `schema` means malformed typed output; `argument` means an ungrounded/invalid input; `context_loss` means repeated or forgotten progress; `planning` means missing/wrong action sequence; `observation` means a tool could not supply needed facts; `termination` means premature or absent clarification/finish; `unauthorized_dispatch` is any fixture launch outside the exact permitted action. This corpus produced planning/termination failures in the final run. It does not cover browser, files, screen pixels, packaged UI or user-profile data. Those need distinct held-out and live evidence.

Phase 3A is not complete: another local model has not been approved/downloaded or compared on this fixed corpus, and the varied/held-out reliability gate is still unmet. The next comparison should use the same corpus and add file/browser cases without tailoring the core runtime to fixture names.
