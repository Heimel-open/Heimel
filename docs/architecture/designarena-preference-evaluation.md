# DesignArena preference evaluation pattern

Status: adopted for VALO Software Factory
Source: https://www.designarena.ai/

DesignArena demonstrates a useful evaluation pattern: identical tasks are sent to multiple models/builders, outputs are compared anonymously, pairwise human preferences are collected, and aggregate relative strength is estimated from those comparisons. Their current methodology also evaluates agentic builders while capturing traces, tool calls, failures, retries and re-prompts.

VALO adopts the pattern, not the authority model and not a required DesignArena dependency.

## Canonical placement

Work item / evaluation task
→ provider-neutral candidate fan-out
→ isolated candidate runs under the same task contract and comparable harness
→ artifact + trace capture
→ blind pairwise evaluation
→ preference evidence / relative ranking
→ independent QC and objective gates
→ VAIG evidence aggregation where applicable
→ REHT authorization for any consequence-bearing promotion/deploy/merge
→ RACS deterministic outcome contract
→ gateway/tool execution
→ Veritas receipt

Preference is evidence. It is never authority.

## Adopted invariants

1. Same task contract for compared candidates. Provider-specific capability differences must be recorded rather than silently changing the task.
2. Candidate identity is hidden from human preference evaluators until their vote is sealed where blind evaluation is feasible.
3. Left/right ordering and candidate presentation order are randomized to reduce position bias.
4. Pairwise votes are immutable evidence records bound to evaluator, task digest, candidate artifact digests and evaluation timestamp.
5. Ranking is derived from pairwise outcomes. Bradley-Terry/Elo-style estimates may be used for relative quality, but the score is not a release or execution permit.
6. Subjective preference and objective correctness remain separate channels. Tests, security gates, policy, evidence sufficiency and authority can veto a preferred candidate.
7. Agentic comparisons must capture execution traces, tool calls, retries, failures, cost/latency and final artifact—not just screenshots or final prose.
8. Model/provider names, harness version, tool surface, prompt/task digest and environment digest are retained in sealed evidence even when hidden from the evaluator.
9. New providers can enter as replaceable competitors through existing provider-neutral adapters; no governance code may depend on a specific model vendor.
10. No preference result can merge, deploy, publish, purchase, send, mutate production or expand authority without fresh REHT clearance at the execution boundary.

## Factory use

The pattern applies beyond visual design. Arenas can be created for frontend/UI, full-stack builds, mobile, slide generation, code changes, refactors, tests, documentation, research outputs and agent trajectories.

Factory routing should therefore distinguish three signals:

- objective admissibility: tests, policy, security, schemas, invariants and evidence sufficiency;
- subjective or outcome preference: human pairwise choice, task-owner preference or downstream observed outcome;
- execution authority: REHT only.

A candidate may win the preference arena and still be rejected by objective QC or REHT. A technically valid candidate may lose on human preference and therefore not be selected. These are intentional, independent decisions.

## Learning loop

Sealed comparison outcomes feed Factory Experience Memory and model/provider routing as historical evidence. They may improve future candidate sampling and routing, but past wins never create current authority and must be freshness-bound to task class, harness version, provider/model version and environment.

## External integration

DesignArena leaderboard/API data may optionally be consumed as a routing prior if licensed/attributed appropriately. External rankings are weak prior evidence only; VALO should prefer its own task-specific, harness-specific and outcome-specific evidence for production routing.
