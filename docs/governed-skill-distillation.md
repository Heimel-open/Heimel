# Governed Skill Distillation

Status: adopted Factory principle

Research basis:

- arXiv:2608.07885, *Reasoning Models Can Be Effective Without Reasoning*.
- arXiv:2608.03573, *SFT Conflicts, RL Coexists: A Theoretical and Empirical Analysis of Multi-Task Learning for LLMs*.

## Principle

Use expensive reasoning as a discovery and learning resource, not as a permanent runtime requirement.

A reasoning-capable worker may discover a reusable procedure from successful trajectories. VALO Factory can distill that procedure into a compact skill or specialized model for cheaper execution. Distillation transfers capability; it never transfers authority.

## Governed lifecycle

1. Run candidate tasks in sandbox/shadow mode with an admissible reasoning worker.
2. Capture trajectories, evidence, inputs, outputs, provenance and evaluation results.
3. Admit only trajectories that satisfy the active governed workspace and completion criteria.
4. Distill recurring procedures into a versioned skill or specialized model.
5. Evaluate the distilled artifact independently against held-out tasks, negative cases and conformance requirements.
6. Bind the artifact to explicit purpose, scope, capability, provenance, model/runtime digest and admissibility state.
7. Execute inside a governed workspace through the canonical authorization chain: VAIG -> reht -> RACS -> external PEP -> Veritas.
8. Escalate to deeper reasoning, DEFER, STEP_UP or DENY when coverage, evidence, conformance, freshness or authority is insufficient.

## Authority invariant

A distilled skill answers: `How can this class of task be performed?`

It does not answer: `May this action be performed now?`

Learning a procedure therefore grants no execution authority. Current state, purpose, scope, evidence and authority are evaluated at execution time. reht remains the commit-time authorization boundary.

## Factory consequence

The model factory should optimize for the cheapest admissible capability that can correctly complete the governed work unit. Frontier reasoning is used where discovery, ambiguity or novelty requires it. Reusable competence is compiled downward where evidence supports doing so.

This creates a governed deep-to-wide loop:

`reasoning discovery -> governed trajectories -> skill distillation -> independent evaluation -> admissibility -> governed runtime -> receipts -> re-evaluation`

Shadow-mode observations can therefore serve two purposes: model routing and generation of candidate training material for function-specific skills/models. Training material remains candidate material until admitted; successful execution alone is not sufficient.

## Parallel-RL capability composition

The Parallel-RL result adds a second implementation pattern for function-specific models. In the evaluated settings, RL updates are sparse and approximately orthogonal across tasks, motivating independent capability training followed by composition.

VALO uses this as a bounded Factory pattern:

`one admitted base -> independent RL capability jobs -> versioned capability candidates -> independent evaluation -> governed composition candidate -> new admission/promotion decision`

Each capability retains its own dataset, reward/objective, engine/runtime, delta and evaluation lineage. Composition is treated as a new candidate artifact and must be evaluated again for interference, regressions and conformance. Individual capability success is necessary but not sufficient for composition admission.

`lib/parallel_rl.py` implements the deterministic candidate-only composition manifest. `tests/test_parallel_rl.py` enforces shared-base lineage, unique capability/delta identity, evaluation evidence, negative/compatibility receipts, no authority transfer and no automatic promotion.

The research result is evidence for modular development, not proof that arbitrary model deltas are universally safe to merge.

## Failure and escalation

A distilled artifact must not silently improvise outside its admitted envelope. Out-of-distribution inputs, missing evidence, changed authoritative state, failed conformance or insufficient authority trigger explicit escalation rather than unsupported completion.

The objective remains correct completion, including correct stop/defer/step-up outcomes, not maximum autonomous completion rate.
