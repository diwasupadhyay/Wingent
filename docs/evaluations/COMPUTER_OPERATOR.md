# Computer Operator Evaluation

Updated: 2026-10-05. Source marker: `operator-v24`. Native adapter, autonomous model and packaged evidence are separate.

## Reference and architecture review

See [both source reviews](SELF_OPERATING_REFERENCES.md). Wingent sends the original goal, bounded action context and current approved screenshot/UIA to a local model; the host validates one action, obtains approval as needed, dispatches and observes again. No fixture workflow is installed in the generic computer adapter.

## Failures that informed this release

- Production mixed legacy desktop observation IDs with computer frames; the reduced computer-only model harness hid that conflict. Production now exposes one protocol and the harness uses its catalogue.
- An empty installed-app search caused immediate termination. A real-model run reproduced this after one model call/18.12 seconds. Running-window discovery is now the fallback.
- The next run reached the field but stopped because a focused generic Pane cleared input targeting: 5 calls/97.16 seconds. Visual click targeting now survives opaque containers; semantically focused non-input controls still clear it.
- A subsequent model run applied the exact greeting. The fixture-owned output matched, but the model proposed a repeated Apply click and hit the duplicate guard: 6 calls/170.36 seconds. One bounded reassessment now asks it to inspect the current result before stopping or acting differently. That timing overlapped build/test activity; it is not a controlled performance benchmark.
- The follow-up evaluation/build session was interrupted by a new user turn; its terminal output was unavailable. Do not count it as another autonomous pass.
- Ollama was unavailable at the start of two evaluations; both failed before dispatch. The installed service was restarted explicitly before retrying. During the final run, `ollama ps` reported 4.5 GB allocation, 8192 context and 60%/40% CPU/GPU placement. This is a likely contributor to latency, not a controlled causal benchmark.
- Native gesture fixture initially hit Windows focus denial during startup. After the fixture finished its own focus initialization, hover and drag were recorded by the app and wait produced a fresh frame. No runtime focus bypass was added.

Earlier important fixes remain: per-thread physical-pixel DPI coordinates, DWM visible bounds, paced Unicode input to avoid Notepad corruption, strict typed nullable schemas, stale-frame refusal and honest partial results.

## Live native results

`scripts/evaluate-native-computer.py` creates a unique scratch document and new Notepad/Calculator windows only.

- Notepad typed/saved the expected text; independent file read-back matched.
- Calculator entered 7 times 8; UIA exposed `Display is 56`.
- One desktop-scoped task switched to the new Calculator, then back to its owned Notepad without a second grant.
- Both applications passed before and after the cross-window update.

`scripts/evaluate-gestures.py` uses a new canvas window. Its own event output confirmed hover and drag; bounded wait returned a fresh frame. This is a native adapter test, not an autonomous model pass.

## Model evidence

`scripts/evaluate-computer.py --autonomous` uses the production tool catalogue with a fixture-scoped window observer and grants approval only for that fixture window. The independent oracle reads the app's applied value. It does not auto-approve desktop-wide or consequential actions.

The v24 run above produced the correct applied greeting but initially stopped via the repeat guard. Model/whole-goal production status stayed unverified. Historical v18 reduced-catalogue testing passed once in 6 calls/103.58 seconds; that does not establish production-catalogue reliability.

Post-gesture run: the independent applied-value oracle matched again (6 model calls, 220.30 seconds), but the final decision timed out while native compilation was running. This is an execution-effect pass and a clean-stopping failure, not end-to-end success. The harness now requires both matching fixture state and a final (not error/clarification) event, so an oracle match alone cannot hide a runtime timeout.

The no-build repeat also matched the app result but timed out during reassessment: 7 calls/200.77 seconds, `clean_stop=false`, evaluator exit 1. Compilation is therefore not the sole cause. Reassessment now keeps the large system prefix stable and puts rejection feedback in task context, allowing provider prefix reuse; its effect must be measured rather than assumed.

Final prefix-stable repeat: correct app effect, 7 calls/199.30 seconds, but final reassessment again timed out; strict evaluator exit 1. No meaningful speed or clean-stopping improvement is established by that change. Native control is working in these fixtures; general autonomous completion remains an open failure, not a completed phase. Budgets were not increased to hide it.

Current evidence is far short of the plan's varied/held-out/repeated gate. No claim of arbitrary application competence or real YouTube playback follows.

## Contract/build evidence

Before the generic-gesture addition: 239 backend tests, 18 frontend tests and one Rust runtime/instance test passed. Sidecar compilation succeeded. The previous Tauri build's terminal output was lost on turn interruption; its artifact timestamp changed, but that alone is not release verification. Final post-gesture tests/build/startup evidence is recorded below when checked.

## Final v24 build checkpoint

- Final backend suite: 246 passed. Frontend: 18 passed. Rust runtime/instance contract: 1 passed.
- Sidecar rebuilt successfully; Tauri `--no-bundle` release build and frontend compilation succeeded.
- EXE: `src-tauri/target/release/app.exe`, SHA-256 `84CDF70DD75A3EC52077C26C80B1EB25EACD7657EC39E2AB0C940E2F1807DC96`.
- Source and adjacent release sidecar hashes match: `2882C420E12902B111D3C489ED5FC762EA788FFDBE51D304B31E9A784785D4B7`.
- Rebuilt EXE launched (PID 21564 at this check). Its owned backend on loopback port 50077 reported `operator-v24`, matching per-run instance prefix `21564`, and model readiness for `qwen3-vl:4b-instruct`. Capability inspection confirmed all eight generic actions and zero legacy desktop/screen tools. Ports/PIDs change each run; do not hardcode them. This is packaged startup/schema evidence, not a full packaged autonomous UI pass.
- Project Markdown links and `git diff --check` pass. Reference clones have clean worktrees, are ignored, and no reference files are tracked by Wingent.

## Boundaries and next checks

Input acceptance is not goal correctness. General verification, model stopping/latency, sensitive custom surfaces, multi-monitor DPI and interrupted-task recovery remain open. Capture/input target one foreground window even in desktop scope; whole-desktop/background/elevated surfaces are not implemented.

Next: repeat the production-catalogue autonomous fixture after the final recovery changes, test varied unfamiliar apps and dialogs, and verify the rebuilt EXE's exact owned backend, model readiness and tool schema. Never silently enlarge budgets or approve unrelated targets.
