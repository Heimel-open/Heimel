# FG-001 — Correct Unknown as a Frontier Signal

Status: OPEN_QUESTION  
Origin: human seed  
Axes: WHAT, WHY, HOW

## Seed

A model saying **"I don't know"** can be a higher-value outcome than producing a plausible answer.

The core hypothesis is not that uncertainty is inherently valuable. It is that a system's definition of a successful answer is often too narrow.

A useful answer state may be:

- `KNOWN`
- `PROBABLE`
- `UNRESOLVED`
- `INSUFFICIENT_EVIDENCE`
- `I_DONT_KNOW`
- `NEED_TO_ASK`
- `CONTRADICTION`
- `KEEP_OPEN`
- `TEST_NEXT`
- `LINK_FOUND`

The candidate objective is therefore:

> **Improve the state of understanding, rather than merely produce an answer.**

## Why this may matter

Answer-optimised systems are pushed toward closure: one conclusion, one recommendation, one explanation. That can destroy useful possibility space when the evidence does not yet support closure.

A precise `I_DONT_KNOW` may instead expose a frontier:

> **KNOWN tells us what can be used. DON'T KNOW tells us where value may still be hiding.**

In that framing, unresolved questions are not automatically defects or backlog debt. Some are research options whose value depends on preserving them long enough for new evidence, mechanisms or cross-frontier links to emerge.

## Connection to Tofoo

Tofoo already preserves hypotheses, contradictions, falsification conditions and unresolved mechanism gaps instead of forcing them prematurely into validated claims. The Frontier Garden can make that behavior explicit and operational for model swarms.

The Garden should therefore distinguish:

`CORRECT_UNCERTAINTY != FAILURE`

and

`CLOSURE != COGNITIVE_PROGRESS`

## Connection to Honest Evaluation

The same pattern appears in evaluation and execution work: unsupported completion can be worse than correct non-completion. `I_DONT_KNOW`, `INSUFFICIENT_EVIDENCE`, `OUTSIDE_MANDATE`, `NEED_TO_ASK`, `DEFER` or `STEP_UP` can be correct terminal or intermediate states when their conditions are actually met.

This file does not claim that the same mechanism governs research and execution. It records the structural analogy as an open question.

## Open questions

1. Can a model reliably distinguish **correct uncertainty** from lazy refusal or under-reasoning?
2. What evidence is required before `I_DONT_KNOW` is considered the optimal state rather than an incomplete attempt?
3. Can preserving an unresolved contradiction improve later discovery compared with forcing an early resolution?
4. Which unresolved states should remain open, and which should trigger immediate acquisition of evidence?
5. Can a swarm identify when two independent `DON'T_KNOW` frontiers are actually the same missing mechanism?
6. Does optimizing for **state-of-understanding improvement** outperform answer-production objectives on long-horizon research tasks?

## Candidate falsifiers

This seed becomes substantially weaker if controlled tests show that:

- explicit unknown/unresolved states do not improve calibration or downstream discovery;
- models use `I_DONT_KNOW` primarily to avoid tractable reasoning;
- preserving unresolved states systematically reduces later solution quality compared with forced closure;
- or the proposed state vocabulary adds no useful discrimination beyond calibrated confidence.

## Swarm invitations

- `DERIVATION`: formalize the distinction between answer completion and understanding-state improvement.
- `SYNAPSE`: connect this frontier to other Tofoo questions where preserved uncertainty may have produced later value.
- `FALSIFIER`: design the cheapest test that could show the idea is useless.
- `COUNTEREXAMPLE`: find cases where forced closure is clearly better than preserving uncertainty.
- `BRIDGE`: test whether Honest Evaluation, Frontier Garden and long-horizon cognitive continuity are manifestations of one deeper state-transition problem.

## Boundary

This is a seed, not a validated result.

`I_DONT_KNOW != TRUTH`

`UNRESOLVED != VALUE`

`FRONTIER_SIGNAL != AUTHORITY`
