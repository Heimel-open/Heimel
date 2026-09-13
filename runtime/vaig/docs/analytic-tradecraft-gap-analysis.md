# Structured analytic tradecraft in VAIG

Status: implemented P0 on `feat/analytic-tradecraft-gate`  
Source reviewed: `tabalizer/Intelligence-Analysis` at `04d204d23f83946832076303c4b28ef48284370c`

## Decision

Adopt selected structured analytic techniques as a deterministic pre-evaluation gate inside VAIG.

Do not create a separate authority-bearing factory. The gate evaluates the quality of represented evidence and analysis. It never authorizes or executes an action.

```text
Reality
  -> Speider / BARO representation
  -> Analytic Tradecraft Gate
  -> VAIG evaluation
  -> REHT clearance
  -> RACS contract / enforcement receipt
  -> Execution
```

## Existing VAIG overlap

VAIG already contained important parts of intelligence-analysis tradecraft:

- `AlternativeHypothesis` preserves multiple explanations.
- Epistemic underdetermination prevents manufactured certainty.
- Auxiliary assumptions and discriminating tests are explicit.
- Consequence divergence separates shared bounded action from cases requiring review.
- Scout, Dirigent and Ensemble provide contextual routing and multiple evaluators.
- WORM and receipt paths preserve evaluation evidence.

The missing capability was not generic critical thinking. It was a deterministic contract for judging the quality of the evidence and analytic process before VAIG consumes the result.

## Confirmed gaps

### P0 gaps implemented

1. Evidence integrity gate
   - provenance known
   - first appearance identifiable
   - manipulation or context drift flag
   - disposition: `CITE`, `BACKGROUND`, `HOLD`, `DISCARD`

2. Independent corroboration
   - citation requires a configurable minimum number of independent confirmations
   - uncorroborated or high-influence-risk material is background only

3. Key assumptions check
   - assumptions are explicit objects
   - status: `STRONG`, `QUESTIONABLE`, `HIGH_RISK`
   - an unsupported collapse assumption blocks a high-consequence case

4. ACH-style contradiction matrix
   - citable evidence is mapped to hypotheses it supports or contradicts
   - ranking selects the hypothesis least contradicted by the evidence
   - ties remain `CONSTRAINED`; they are not converted into false consensus

5. Analysis of absence
   - expected observations are explicit
   - missing expected observations remain visible and constrain the assessment

6. Authority boundary
   - `execution_authority = false`
   - `requires_reht_clearance = true`
   - `INSUFFICIENT` blocks consequential action
   - `CONSTRAINED` requires human review without granting authority

### P1 gaps not implemented in this PR

- longitudinal source reliability and correction history
- Bayesian updating of source and hypothesis confidence
- policy-owned probability thresholds tied to consequence and action cost
- indicators-and-warning monitoring across time
- chronology and event-sequence anomaly engine
- network provenance and circular-citation detection
- calibration of human and machine analytic performance through SAGE

These are non-blocking follow-on work. They should not expand the P0 runtime contract before its deterministic behavior is validated.

## Technique-by-technique placement

### VAIG analytic tradecraft gate

- `BCRAAP Source & Information Evaluation.MD`
  - evidence integrity, credibility, corroboration, purpose risk and citation disposition
- `Analysis_of_Competing_Hypotheses_(ACH).md`
  - contradiction-first ranking and discriminating evidence
- `Key_Assumption_Check.md`
  - explicit assumptions and collapse risk
- `Multiple_Hypothesis_Generation.md`
  - preserve multiple viable explanations; do not anchor prematurely
- `Logical Reasoning.md`
  - abduction, deduction and induction as a repeatable evidence cycle
- `Known_Unknown.md`
  - explicit knowledge gaps and unknown-risk representation
- `Cronologies_&_Timelines.md`
  - event order, gaps and inconsistencies; P1 temporal engine
- `Bayesian How To.md`
  - P1 calibration and policy-bound probability updates, not hard-coded runtime authority
- `5W1H Operational Analysis.MD`
  - canonical case completeness: what, when, where, who, how, why and consequence

### Speider / BARO / case preparation

- `Brainstorming.md`
  - divergent collection and hypothesis generation before filtering
- `Starbursting_5W1H.md`
  - question generation and collection requirements
- `Network_Analysis.md`
  - entity, relationship and provenance graph construction
- operational portions of `5W1H Operational Analysis.MD`
  - normalization of event, actor, time and location fields

These techniques create or normalize observations. They must not independently determine admissibility.

### SAGE evaluation and calibration

- `12_images_of_intelligence.md`
  - evaluator-lens diversity, falsification, objectivity and critical-rationalism calibration
- `Outside-In_Thinking.md`
  - external-context challenge sets
- `Red_Hat_Analysis.md`
  - capture intuition as a weak signal for review, never as authorization evidence
- Bayesian source and analyst track-record calibration from `Bayesian How To.md`

SAGE can train, compare and calibrate judges using these techniques. SAGE must never gain execution authority.

### EMOS Enterprise Flight Simulator

- `Key_Driver_Analysis.md`
- `Scenario_Planning.md`
- `Cone_of_Plausibility.md`
- `What_If_Analysis.md`
- `Decision_Trees.md`
- `Impact_Matrix.md`
- `SWOT_Analysis.md`

These are strategic exploration and decision-support techniques. They belong in simulation, policy testing and scenario evaluation rather than the VAIG runtime gate.

## Deliberate non-adoptions

- Intuition is not treated as truth or authorization evidence.
- SWOT, impact matrices and decision trees do not become runtime admissibility rules.
- Bayesian thresholds are not embedded as universal constants; consequence thresholds belong to policy and require calibration.
- The gate does not infer source reliability from prestige, domain suffix or presentation quality.
- The gate does not replace qualified human judgment. It structures where ACE should be invested.

## Runtime contract

Inputs:

- `EvidenceItem`
- `AlternativeHypothesis`
- `KeyAssumption`
- `ExpectedObservation`
- consequence flag and corroboration policy

Outputs:

- `TradecraftState`: `SUFFICIENT`, `CONSTRAINED`, `INSUFFICIENT`
- evidence dispositions
- assumption status
- hypothesis support and contradiction counts
- least-contradicted hypotheses
- discriminating evidence references
- missing expected observations
- human-review and halt signals
- explicit no-authority boundary

## Acceptance criteria

- Unknown provenance or suspected manipulation can never produce `CITE`.
- No citable evidence fails closed as `INSUFFICIENT`.
- High-purpose-risk or uncorroborated material remains background only.
- A high-risk collapse assumption blocks a high-consequence case.
- Competing hypotheses are ranked by contradiction before support.
- Equal least-contradicted hypotheses remain constrained.
- Missing expected observations are preserved in output.
- The assessment never grants execution authority.
- Existing orchestrator behavior remains unchanged when no tradecraft inputs are supplied.

## Source limitation

The reviewed repository is a practical cheat-sheet collection inspired by structured analytic techniques. It is useful for method extraction, but it is not treated as binding police, PST or intelligence-service doctrine. Production policy and calibration must be independently validated against authoritative standards and domain experts.
