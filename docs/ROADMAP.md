# Wingent Roadmap

Updated: 2026-10-03. The latest request authorizes scoped implementation and evaluation.

The product is a general-purpose personal computer agent. The user supplies a goal; Wingent discovers and combines capabilities to achieve it. Applications are adapters and test fixtures, not separate product phases.

The sole detailed tracker is [AGENT_IMPLEMENTATION_PLAN.md](AGENT_IMPLEMENTATION_PLAN.md).

| Phase | Layer | Current status |
| --- | --- | --- |
| 0 | Audit and rollback baseline | Historically complete |
| 1 | Application-independent runtime | Complete for recorded runtime contracts |
| 2 | Typed capabilities and bound approvals | Complete for current contracts |
| 3 | Reliable reasoning, working context and skill discovery | In progress; frozen four-case app corpus passes 1/4 with current model in either prompt variant; alternative model comparison pending |
| 4 | Structured computer observation/action | Native app discovery/approved launch, experimental Chrome, Win32 controls and files exist; live cross-app control/playback not verified |
| 5 | Controlled process/code execution | In progress; discovery and approved native execution added, cancellation/recovery not complete |
| 6 | Vision and input fallback | Planned |
| 7 | Cross-capability reliability and release readiness | Planned |

Next: expand the live corpus and held-out cases, measure repeat/stop behavior, improve explicit remaining-work and evidence-grounded verification, and harden continuation across disconnects. In-memory clarification resume is implemented. An alternative-model pull was attempted but blocked by outbound network access; no comparison was possible.

Then add Windows/accessibility, browser DOM and application APIs as peer adapters; controlled process execution and visual fallback follow their safety prerequisites. Security, recovery, evaluations and packaging are continuous work, not a final cleanup phase.

A rebuilt EXE, passing unit tests or an accepted tool call does not prove reliable goal completion. See the plan for recorded evidence, pending decisions, proposed evaluation thresholds and release gates.
