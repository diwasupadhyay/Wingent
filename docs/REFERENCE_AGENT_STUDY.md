# Reference computer agents: source study

Reviewed: 2026-10-06. **Research only; this document does not implement or authorize changes.**

Historical study: the reference-code analysis remains useful, but the Wingent comparison below describes the removed runtime at `4e3b3ca`, not today's architecture or protections. Use [the current plan](SELF_OPERATING_AGENT_PLAN.md) and [current structure](../STRUCTURE.md). Old source paths below are historical references, not files expected in this checkout.

## 1. Scope and evidence

This study follows the execution paths in the locally cloned repositories, not just their README claims or demonstration videos.

| Project | Local checkout | Inspected revision |
| --- | --- | --- |
| OthersideAI Self-Operating Computer (SOC) | `references/self-operating-computer/` | `fac568eea7da5e24f8bc91bfc1211b65679177eb` |
| AmberSahdev Open-Interface (OI) | `references/Open-Interface/` | `5a4f706223507fc9d9eb2239cced85385fcb1308` |
| Wingent comparison baseline | This repository | `4e3b3ca` |

The references were read, not executed or modified. No desktop actions, model requests, dependency installations, or builds were performed for this study. Source inspection establishes how code is intended to execute; it does **not** prove reliability on this PC. Provider identifiers and SDK usage below describe these revisions, not a recommendation that their APIs still work unchanged.

The principal loops, prompts, input executors, screenshot utilities, model routing, and key adapter implementations were inspected. This is not an exhaustive audit of every dependency, UI widget, or provider branch.

## 2. The central finding

Both projects implement a relatively small feedback loop:

```text
User goal + current screenshot + available context
                         |
                         v
                 Vision/LLM adapter
                         |
                         v
                Structured action list
                         |
                         v
                 Mouse/keyboard executor
                         |
                         v
           New screenshot on the next model round
                         |
                  Continue or finish
```

Their generality comes from **giving a model visual observations and general input primitives**, not from an automation for each application. Opening software through OS search is usually a sequence proposed by the model, not a separately trained application launcher.

However, neither inspected main loop supplies a general, independent proof of completion. Both can trust a model's completion claim. Both normally observe between **action batches**, not after every individual input. A convincing demo is not evidence of universal task reliability.

## 3. Self-Operating Computer

### Architecture and control flow

Source owners:

- [Main loop and dispatch](../references/self-operating-computer/operate/operate.py): `main`, `operate`.
- [Provider adapters](../references/self-operating-computer/operate/models/apis.py): `get_next_action`, provider calls, OCR/label conversion, JSON cleanup and fallback.
- [Prompts](../references/self-operating-computer/operate/models/prompts.py): standard, OCR and labeled operation contracts; OS-specific shortcuts.
- [Input implementation](../references/self-operating-computer/operate/utils/operating_system.py): `OperatingSystem.write`, `press`, `mouse`, `click_at_percentage`.
- [Screenshots](../references/self-operating-computer/operate/utils/screenshot.py), [OCR](../references/self-operating-computer/operate/utils/ocr.py), [labels](../references/self-operating-computer/operate/utils/label.py).

`main` obtains a goal, constructs an OS-specific system prompt, initializes conversation messages and repeatedly calls `get_next_action`. The selected adapter captures a screenshot and requests operations. `operate` executes the returned list sequentially. A `done` operation ends the task; an unknown operation also stops execution. The loop stops after its counter exceeds 10: up to 11 action rounds, assuming no earlier stop. Provider-internal recursive retries are outside that bound.

The normal action vocabulary is deliberately small:

| Operation | Actual behaviour |
| --- | --- |
| `write` | Replaces literal `\\n` with newline and calls `pyautogui.write` character by character. |
| `press` / `hotkey` | Both dispatch to the same method: hold every listed key, wait 0.1 seconds, release every key. This is chord behaviour, not a sequence of independent presses. |
| `click` | Convert fractional screen coordinates to pixels, move the pointer, trace a small circle, then click the target. |
| `done` | Print the model's summary and stop; no runtime verifier checks it. |

`operate` sleeps one second before **each** operation. Pointer movement defaults to 0.2 seconds, followed by approximately 0.5 seconds of circular movement. The circle is visual presentation, not reasoning or evidence of a successful click.

### How it opens applications

The prompt teaches OS search: Windows/Linux use the Windows key; macOS uses Command+Space. The model can then emit app-name typing and Enter. The standard example even assumes the named application will be available. This is a prompt example, not observed-result validation or a Windows installed-app discovery subsystem.

The useful concept is a reusable OS-navigation skill. The weakness is blindly submitting a search without checking whether the highlighted result is the intended app.

### Seeing and locating targets

The Windows screenshot path uses `pyautogui.screenshot()` and saves to disk. Despite the helper name `capture_screen_with_cursor`, this branch does not explicitly draw a cursor; macOS explicitly requests one through `screencapture -C`.

Three targeting approaches appear in the adapters:

1. **Direct visual coordinates:** model returns fractions such as `0.5`; executor multiplies them by screen width/height.
2. **OCR grounding:** model names text to click; EasyOCR finds text boxes; their centres are normalized against screenshot dimensions. The matcher uses substring matching and retains the last match, so repeated labels can be ambiguous. Some adapters construct an EasyOCR reader inside each click-processing pass.
3. **Set-of-marks:** YOLO detects regions, the helper draws numbered labels, the model chooses a label, and the adapter resolves its box centre. This requires detector weights and extra processing. The inspected labeled adapter has `return processed_content` inside its operation loop, so it can return after only the first operation.

The executor's coordinate space is the screen, not Wingent's 0–1000 window crop. These are incompatible contracts unless explicitly transformed. Multi-monitor origins and Windows scaling require separate validation; these helpers do not establish a comprehensive Windows DPI/multi-monitor solution.

### Models, history and recovery

`get_next_action` explicitly routes model names to adapters. The inspected routes include GPT-family direct/OCR/labeled variants, Qwen OCR, Gemini vision, Claude OCR, and Ollama LLaVA. The `agent-1` route returns a placeholder, not a working implementation.

In the standard GPT path, screenshots and assistant operation responses accumulate in `messages`. This supplies history but increases payload size. The Ollama path removes the latest image reference from stored history after inference, retaining textual continuity without repeatedly loading all earlier image paths.

JSON handling strips Markdown fences then uses `json.loads`; it is not a strict typed action schema. Some errors trigger recursive retries; OCR failures can fall back to direct GPT vision. That fallback may change provider requirements and cost. Some exception paths reference `content` before it is necessarily assigned.

Input wrappers catch exceptions and print them instead of propagating a structured failure result. Therefore the outer loop may continue without knowing that typing or clicking failed. Key release is not protected by a universal `finally` block in the chord implementation.

The separate `evaluate.py` contains screenshot-based model evaluation; that is **not** an independent verifier integrated into normal `operate` execution.

### What to learn, not copy

Keep the simple visual action vocabulary, original goal, OS-aware shortcuts, and optional OCR/label grounding. Do not copy swallowed input errors, recursive unlimited retries, decorative cursor circles, unbounded image history, or automatic cross-provider fallback.

## 4. Open-Interface

### Architecture and control flow

Source owners:

- [Application coordination](../references/Open-Interface/app/app.py): queues and worker threads connecting GUI and core.
- [Agent loop](../references/Open-Interface/app/core.py): `execute_user_request`, `execute`, interruption flag.
- [LLM facade](../references/Open-Interface/app/llm.py) and [factory](../references/Open-Interface/app/models/factory.py).
- [Interpreter](../references/Open-Interface/app/interpreter.py): model JSON to PyAutoGUI calls.
- [Prompt contract](../references/Open-Interface/app/resources/context.txt).
- [Screen utilities](../references/Open-Interface/app/utils/screen.py), [local information](../references/Open-Interface/app/utils/local_info.py), [settings](../references/Open-Interface/app/utils/settings.py).

The GUI enqueues a request; a worker starts `Core.execute_user_request`. `Core.execute` asks the adapter for instructions, executes their `steps`, and either returns the `done` text or recursively calls itself with a larger `step_num`.

The model receives the original request, step number and a current screenshot. Ordinary responses contain `steps` with function names, parameters and user-visible justifications, plus `done` (empty/null while unfinished). An empty parsed object gets one additional model attempt. Interpreter failures stop the request. No explicit overall recursion/step/time budget is present in this core loop.

`App` uses threads for execution and queue communication, even though it imports multiprocessing queues. UI status messages are queued and drained using Tk's `after(200, ...)`. This is a useful separation of execution from UI work, not evidence that all operations run in separate processes.

### Typing, mouse and keyboard

`Interpreter.execute_function` strips a `pyautogui.` prefix and dynamically resolves functions with `hasattr/getattr`.

| Input | Implementation detail |
| --- | --- |
| Typing | Accepts `string`, `text` or `message`; default interval 0.1 seconds. The prompt suggests approximately 0.05 seconds. |
| Sequential keys | `press` accepts a key/list, repetitions and interval. |
| Chords | `hotkey` expands a key list into positional arguments. |
| Pointer/scroll/drag | Generally forwards parameters to the named PyAutoGUI function; ordinary coordinates are pixels. |
| Waiting | Special-cases `sleep` using the `secs` parameter. |

An unconditional `pyautogui.press("command")` runs before each interpreted function as a warm-up workaround. That is macOS-oriented behaviour, not a sound Windows focus-management mechanism.

Unknown function names merely print a message. Since no exception is raised, `process_command` can return success for an action that did nothing. Dynamic attribute lookup is not a validated allowlist of safe input primitives.

Typing uses PyAutoGUI, not an observed Unicode read-back protocol. Do not assume reliable international text entry, correct focus, clipboard preservation or successful insertion just because the call returned.

### Prompts and speed strategy

The prompt explicitly recommends:

- Short batches of about 4–5 steps to reduce API round trips.
- A fresh screenshot after complicated navigation or uncertain transitions.
- Keyboard shortcuts where practical and low typing delays.
- Checking actual focus before typing and the latest screenshot rather than trusting history.
- Waiting for applications to load, avoiding overwriting user data, and stopping for login.

Many application-launch instructions are specifically about macOS Spotlight. `local_info.py` discovers `.app` names in `/Applications`; on failure it reports `Unknown`. It is not a general Windows installed-application catalogue.

The promising speed improvement is fewer model calls for predictable input—not more arbitrary mouse motion or unlimited CPU usage. The trade-off is that later actions in a batch may use assumptions invalidated by an earlier action.

### Model adapters are materially different

| Adapter | Context and response mechanism |
| --- | --- |
| `gpt4v.py` | Sends prompt context + original goal + step number + screenshot through Chat Completions each round; no explicit prior-action transcript in that request. |
| `gpt4o.py` | Creates an assistant/thread, uploads screenshots and retrieves responses; tracks uploaded image IDs for cleanup. |
| `gpt5.py` | Uses Responses with text/image blocks and an 800-token output limit. It does not pass a previous response ID in this path. |
| `gemini.py` | Sends context, goal, step number and screenshot through Google's SDK; parses the returned JSON text. |
| `openai_computer_use.py` | Tracks response/call IDs, returns screenshots as computer-call output, and converts structured computer actions to interpreter steps. |

The factory routes by exact name or prefix; unknown names fall back to the GPT4v-style adapter. This is extensibility through provider adapters, not automatic discovery of every model's supported features.

Important implementation weaknesses:

- `Screen` encodes PNG, while several ordinary adapters label that data JPEG.
- JSON extraction uses the first `{` and last `}`, without a strict action schema.
- The computer-use adapter declares environment `browser` while executing desktop PyAutoGUI actions.
- It automatically acknowledges pending safety checks rather than asking the user.
- Its scroll conversion only uses vertical delta; its drag conversion reduces a path to endpoints and expects indexable coordinate pairs.
- An unrecognized structured action produces an empty step list. Absence of a computer call can become `Done.` even without an explicit completion explanation.
- The GPT4o adapter's post-poll loop does not refresh `run` inside the loop; unexpected nonterminal states could stall.

These are source observations, not claims that every adapter was exercised against a live service.

### Stopping, privacy and completion

The interrupt flag is checked between steps, not as a universal cancellation mechanism inside inference, typing or sleep. Recursive `execute` resets that flag, and separate request threads can share the core/model state. Robust single-task ownership and cancellation still need design work.

`done` is model-reported completion. Prompt instructions to verify a screenshot do not create a separate host-side verifier, and a response can contain both actions and a completion message before the effects of those actions are observed.

Settings store the API key base64-encoded in a JSON file: encoding is not encryption. Screenshot helpers can write local files; the Assistants adapter uploads images and attempts cleanup later. Its Gemini adapter explicitly lowers configured content-safety thresholds. These are not privacy/safety patterns to carry into Wingent unchanged.

## 5. Historical comparison with Wingent at 4e3b3ca

| Concern | References | Wingent baseline | Remaining issue |
| --- | --- | --- | --- |
| Brain/executor split | Model adapters propose input; interpreter executes | `brain.py`, `operator.py`, registry and `runtime.py` already separate these | Improve state transitions, not merely add another planner class. |
| General input | PyAutoGUI primitives | Native Windows input, UIA, pointer/keyboard/scroll/drag primitives | Existing capabilities need real cross-app reliability evidence. |
| Observation | Primarily screen screenshots per round | Granted-window screenshot + UIA + frame identity | Desktop scope follows windows; it is not a full virtual-desktop overview. |
| App launch | Model-generated OS search sequence | Discovery/direct launch plus new observed Windows Search entry | Search-to-app handoff and packaged-window identity still need manual validation. |
| Action granularity | Multiple operations per model round | Usually one tool decision per round | Extra inference/schema/observation overhead can dominate simple tasks. |
| Context | Varies from screenshot-only rounds to growing conversations | Bounded task history, plans, results and current frame | Keep one coherent current-state record without repeated schemas/UI trees. |
| Completion | Mostly trusts model `done` | Honest accepted/unverified states; limited concrete verification | Need general outcome assessment without equating accepted input with success. |
| Safety | Mostly prompts or loose dispatch | Typed schemas, task ownership, stale-frame checks and approvals | Preserve safeguards while eliminating redundant grants for ordinary work. |
| Recovery | Retry parsing, fallback model, next screenshot | Bounded retries, evidence checks and repeat guards | Recovery must distinguish a harmless refresh from repeating an effect. |

Historical Wingent owners (recoverable at `4e3b3ca`): `backend/app/brain.py`, `operator.py`, `runtime.py`, `computer_tools.py`, `windows_computer.py`, `provider_settings.py`, and `task_state.py`. Most were removed during the SOC replacement.

The recent failure traces show that an application launch can succeed while the subsequent observation/control decision fails. More mouse functions alone cannot fix that. Conversely, stricter verification can expose incomplete work that a reference implementation might simply label done.

## 6. Proposed direction for later implementation — not started here

1. **One authoritative current computer state.** Keep observed foreground/window identity, frame ID, coordinate transform, controls, focused input and last action outcome together. Never reacquire an unchanged grant just to express another intention.
2. **General desktop observation.** Add a deliberate overview mode for OS search, menus and cross-window transitions, with explicit monitor/DPI mapping. Keep focused-window capture as the cheaper default.
3. **Small validated action batches.** Batch only predictable low-risk input in one stable context. Stop and observe at app switches, dialogs, navigation, unexpected focus changes and consequential submissions. Invalidate the rest of a batch when a precondition fails.
4. **A clear action-result contract.** Distinguish not dispatched, dispatched, observed effect, unknown effect, goal satisfied and blocked. Exceptions must reach the loop. Always release held keys/buttons.
5. **Outcome-based verification.** Prefer UIA text, document contents, filesystem read-back or app APIs. Use visual assessment when structured evidence is unavailable, and label its uncertainty. Seeing the expected number is not proof it was written into the requested document.
6. **Efficient context and inference.** Retain the goal, remaining work, compact action ledger and newest image. Send detailed schemas only when needed. Cache expensive observers/OCR safely; measure before changing resource settings.
7. **Recover using new evidence.** If input had no effect, inspect focus/dialogs and choose another target or method. Retry rejected inference separately from computer effects. Do not silently change provider or spend beyond configured budgets.
8. **Responsive UI and stopping.** Keep window creation off the Windows UI thread, make progress accessible, and propagate cancellation through inference and input. A visible Stop button is insufficient if the worker cannot stop.

These are design candidates for the next discussion, not completed phases. No promise of arbitrary-app reliability follows from implementing this list.

## 7. Acceptance checks for that later work

Use normal task prompts, not bespoke code paths for the examples:

- Open an unfamiliar installed app through Windows Search; prove the selected window belongs to the observed result.
- Type punctuation and non-ASCII text into a fresh document; read it back.
- Open a menu, move/click the intended target, dismiss it, and observe dismissal.
- Carry a computed result between applications and verify the destination content.
- Recover from a moved window, delayed launch, popup and failed first click without blindly replaying input.
- Stop during inference, pointer motion and a short batch; no further input after cancellation is acknowledged.
- Test at different Windows scaling settings; verify image-to-screen coordinate mapping.
- Record model-call count, prompt/image size, time to first action, total duration and actual final state. Compare against the same tasks before claiming a speed improvement.

Screenshots or user observations should accompany live results. Mocked tests validate contracts, not real Windows focus or model judgement.

## 8. Reuse boundaries and summary

SOC's checked-in license is MIT; OI's is GPLv3. Record provenance and review licensing before incorporating source. Prefer independently implementing the architectural ideas; do not treat these repositories as interchangeable code snippets. The ignored reference folders remain study material and must not be committed.

**What Wingent should adopt:** visual grounding, simple general input, short feedback cycles, original-goal continuity, and carefully bounded batching.

**What Wingent should retain:** typed tools, local-first operation, honest verification states, screenshot consent, consequential-action approvals and cancellation.

**What Wingent should not imitate:** unchecked dispatch, blind Enter, swallowed failures, unlimited retries, automatic safety acknowledgements, misleading completion, or macOS assumptions on Windows.

The objective is not to make Wingent move the mouse more often. It is to reliably connect **goal → observation → grounded action → observed result → justified next decision** across applications.
