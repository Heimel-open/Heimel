# Epistemic underdetermination

Status: canonical VAIG evaluation contract, wired into `VAIGOrchestrator`.

Primary source: Stanford Encyclopedia of Philosophy, “Underdetermination of Scientific Theory”
https://plato.stanford.edu/entries/scientific-underdetermination/

## Decision

VAIG recognizes `UNDERDETERMINED` as a first-class epistemic state.

It means the current evidence does not justify selecting one surviving explanation, theory or revision target over the relevant alternatives.

It does not mean false, noise, generic uncertainty, evaluator dissent or representation change.

## Forms

- `HOLIST`: a failed prediction implicates a bundle of focal and auxiliary assumptions but does not identify which component must be revised.
- `CONTRASTIVE`: multiple materially distinct alternatives survive the same evidence.
- `MIXED`: both conditions apply.

## Output contract

`EpistemicUnderdeterminationGate.assess()` returns:

- `epistemic_state`: `DETERMINED`, `UNDERDETERMINED` or `INSUFFICIENT_EVIDENCE`
- `kind`: `NONE`, `HOLIST`, `CONTRASTIVE` or `MIXED`
- all surviving alternatives
- shared evidence references
- revision targets
- discriminating tests
- unconceived-alternative risk
- consequence divergence
- explicit rationale
- `execution_authority = false`
- `requires_reht_clearance = true`

## Orchestrator integration

`VAIGOrchestrator.evaluate()` accepts optional epistemic inputs:

- `alternative_hypotheses`
- `shared_evidence_refs`
- `failed_prediction`
- `revision_targets`
- `unconceived_alternative_risk`
- `consequence_divergence`

When these inputs are supplied, the resulting `OrchestratorResult` includes the full underdetermination assessment.

Runtime behavior:

- no epistemic inputs: existing validation flow is unchanged
- multiple alternatives with one common bounded consequence: validation may continue, but execution still requires REHT clearance
- consequence-divergent alternatives: `epistemic_blocked = true`, human review required, `should_halt = true`
- no viable alternative or missing shared evidence: `INSUFFICIENT_EVIDENCE`, `epistemic_blocked = true`, `should_halt = true`

This is fail-closed at the epistemic boundary without treating every unresolved explanation as a universal action ban.

## Boundary with SRI

SRI asks whether meaning and reference survive a representation change. A valid invariant may show that two descriptions are equivalent.

Underdetermination asks whether the same evidence supports more than one materially distinct explanation. A shared observable does not by itself prove equivalent mechanism or theory.

## Routing rule

```text
Multiple explanations survive current evidence
  -> UNDERDETERMINED
  -> preserve alternatives
  -> identify discriminating tests

Failed prediction has several defensible blame targets
  -> UNDERDETERMINED / HOLIST
  -> preserve auxiliary assumptions and revision targets

Alternatives imply the same bounded action
  -> common action may remain eligible for REHT assessment

Alternatives imply different consequences
  -> human review or new evidence before consequential execution

Evidence missing or no viable alternative remains
  -> INSUFFICIENT_EVIDENCE
  -> halt before consequential execution
```

The assessment never grants execution authority. REHT evaluates mandate and admissibility. RACS records the resulting execution or refusal.

## Limits

- The state is relative to current evidence, instruments and auxiliary assumptions.
- Empirical equivalence must be established case by case.
- New observations, interventions or instruments may resolve the state.
- Bare logical possibilities do not receive equal standing with developed, evidentially serious alternatives.
- `UNDERDETERMINED` must not be used to shield a hypothesis from genuine falsification.
