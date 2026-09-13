# L2 VAIG Runtime Layer

Status: draft v1.1  
Scope: governance runtime evaluation context and rich-state assessment  
Boundary: VAIG evaluates represented evidence and runtime conditions; REHT determines present admissibility and clears or refuses the exact action

## Purpose

L2 constructs and evaluates the governed environment used before consequence-bearing execution.

VAIG operationalizes evidence, policy context, authority references, state, uncertainty, risk and receipt requirements into a structured evaluation record for REHT.

VAIG does not create authority or execution clearance.

## Responsibilities

VAIG evaluates:

- evidence condition and provenance
- policy context
- authority references and gaps
- trust state
- risk contract
- criticality and consequence
- uncertainty and calibration
- boundary conditions
- tail-risk and maximum-error exposure
- out-of-distribution status
- representation and granularity consistency
- authoritative-correction status
- receipt requirements
- refusal and resolution handoff conditions

## Inputs

VAIG may consume a standard action/evidence package or, where required, a `RichStateEnvelopeV1`.

Conceptual rich-state input:

```text
s = {
  rich_state_id,
  model_runtime_mal_binding,
  history_scope,
  history_digest,
  state_schema_id,
  state_payload_or_reference,
  state_digest,
  representation_level,
  granularity_level,
  evidence_refs,
  transformation_lineage,
  proposed_action,
  proposed_action_digest,
  alternatives,
  uncertainty,
  boundary_conditions,
  tail_risk_summary,
  out_of_distribution_status,
  reversibility_class,
  known_omissions,
  authoritative_correction_ref
}
```

A state digest proves identity and integrity of the representation. It does not prove truth, completeness or sufficiency.

## Output

VAIG outputs evaluation environment `e`:

```text
e = {
  authority_refs,
  evidence_evaluation,
  policy_context,
  state_evaluation,
  trust,
  risk,
  criticality,
  uncertainty_status,
  calibration_status,
  boundary_risk,
  tail_risk,
  granularity_consistency,
  authoritative_correction_status,
  surviving_alternatives,
  missing_information,
  recommended_outcome,
  conditions,
  receipt_policy,
  rrp_policy
}
```

The recommended outcome uses the canonical vocabulary:

```text
ALLOW
MODIFY
DEFER
STEP_UP
DENY
HALT
```

The output is evaluation evidence for REHT. It is not a clearance or execution permit.

## Relationship to MAL

MAL runs before invocation and admits the exact model, provider, runtime and required output contract.

MAL may require:

- a specific rich-state schema;
- a bounded history scope;
- uncertainty and boundary metadata;
- tail-risk metadata;
- representation and granularity limits;
- authoritative correction;
- prohibition of direct scalar output.

MAL does not evaluate the actual produced state. VAIG does.

## Relationship to REHT

REHT consumes the VAIG evaluation together with current authority, policy, state and consequence conditions.

```text
VAIG evaluates.
REHT determines present admissibility and clears or refuses the exact action.
```

Material changes to the action, state, evidence, authority, policy, representation or granularity require re-evaluation.

## Relationship to RACS and Core

RACS binds:

- the exact action digest;
- rich-state and history digests where used;
- the VAIG evaluation reference;
- the REHT clearance reference;
- constraints, expiry and replay protection.

Core enforces the bound decision at the effect boundary.

VAIG does not directly call consequence-bearing adapters.

## Relationship to RRP

When execution cannot continue normally, VAIG routes refusal, uncertainty, missing evidence or failed correction into RRP where appropriate.

## Prohibited responsibilities

VAIG must not:

- create authority;
- issue REHT clearance;
- treat model self-review as independent correction;
- accept mean performance when tail or boundary risk is unacceptable;
- allow representation or granularity changes to hide consequence;
- reinterpret a state digest as proof of truth;
- execute side effects.

## Contract

```text
MAL admits the model and output contract.
The model proposes.
VAIG evaluates the actual evidence and state.
REHT clears the exact action.
RACS binds the constraints.
Core enforces.
```

See `docs/architecture/rich-state-evaluation-contract.md`.
