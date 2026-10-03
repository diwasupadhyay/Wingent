# Phase 3B: working context and progress

Date: 2026-10-03. Runtime: `operator-v13`. Model: installed `qwen3-vl:4b-instruct` through local Ollama.

## Hypothesis and scope

The old planner retained only six distinct bodies and cut long results into text excerpts. It could lose source data, restart accepted actions, or produce an output before reading all pages. Clarification answers were retained but excluded from name/path grounding.

The implemented slice preserves original intent and optional bounded planning notes, indexes every task record, retrieves historical results without external redispatch, tracks file page/version coverage, and bounds repeated observations. Notes are model interpretations; host record references only establish provenance, not correctness. The original goal and prior requested outcomes remain visible.

## Contract evidence

The backend suite passes 187 tests. Targeted cases cover:

- Eight distinct large results: old records remain indexed, clipping is explicit, and retrieval does not repeat an external action.
- A second task cannot retrieve the first task's results; the shared registry is unchanged.
- Escaped JSON retrieval remains readable instead of being clipped into another unresolvable retrieval.
- Replanning and clarification preserve requested outcomes/constraints; fabricated record IDs are rejected.
- Missing middle pages and changed source versions remain incomplete, even if a later page reports EOF.
- A premature report proposal replans to the missing page without creating the output.
- Alternating A/B observations require a concrete bounded refresh or an intervening state-changing action.
- Clarification answers can supply an app name or output path.

## Live model evidence

Run with `PYTHONPATH=backend`:

```powershell
python scripts/evaluate-operator.py --variant fruit
python scripts/evaluate-operator.py --variant paged
```

Both passed once against source. The fruit task listed an isolated folder, read its source and created a report with the observed counts. The paged task read both source pages, then created a report containing North=17 and South=23. It used `list_directory → read_text → read_text → create_text`, took 124.22 seconds and consumed 11 model calls. Its plan was revised only once; explicit notes alone did not provide reliable ongoing progress assessment.

The evaluator approves only bounded file actions inside a newly created fixture folder (and task-local history retrieval). It requires the expected action sequence and observed output values, refuses overwrite, and asserts that runtime whole-goal verification stays false.

For a separately running rebuilt sidecar, use `--endpoint http://127.0.0.1:8000`. The evaluator checks the current shared runtime marker before submitting work. The paged case passed against the frozen operator-v13 HTTP backend with the full tool catalogue in 172.49 seconds, using the same four-action sequence and correct output values. This is close to the 180-second task limit and is not a performance target. The initial restricted-shell cleanup was denied; exact-PID/path-checked elevated cleanup then stopped the owned test tree. No user application was terminated.

## Remaining limits

These checks complete the bounded 3B task/file context contracts. They do not establish the broader Phase 3 reliability threshold, fresh desktop control, correct web research, or independent semantic verification. Historical results can be stale; notes can omit or misinterpret the goal; a file can change after its last observed page. Report completeness checks currently cover UTF-8 sources and conservatively require complete observed pages, even when a future workflow might intentionally use a subset. Full task continuity still requires restart/disconnect reconciliation.
