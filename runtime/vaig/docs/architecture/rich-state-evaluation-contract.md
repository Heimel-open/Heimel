# Rich-State Evaluation Contract

Status: canonical VAIG architecture mapping  
Date: 2026-08-02  
Scope: VAIG evaluation input and handoff to REHT  
Upstream mapping: `nsolland/Index/architecture/RICH_STATE_AUTHORITATIVE_CORRECTION_MAPPING_2026-08-02.md`

## Purpose

VAIG must be able to evaluate more than a final model answer when a workflow is history-dependent or consequence-sensitive.

The governed input should preserve:

- the relevant history scope;
- the state constructed from that history;
- the representation and granularity level;
- source evidence and transformation lineage;
- the proposed action;
- uncertainty, alternatives and omissions;
- boundary conditions and tail-risk exposure;
- the required authoritative-correction result.

This document defines the conceptual `RichStateEnvelopeV1` consumed by VAIG.

It does not create a new authority layer, decision vocabulary or execution path.

## Canonical path

```text
MAL admits model/runtime/output contract
→ Harness assembles permitted history and invokes
→ model produces RichStateEnvelopeV1 + proposed action
→ VAIG evaluates
→ REHT clears or refuses the exact action
→ RACS binds constraints
→ Core enforces
→ Receipts attest
```

VAIG evaluates. REHT clears. RACS binds. Core enforces.

## RichStateEnvelopeV1

Minimum conceptual fields:

```text
rich_state_id
schema_version
producer_identity
model_id
model_version
runtime_profile_hash
mal_clearance_id
workflow_id
action_case_id
history_scope
history_start
history_end
history_digest
state_type
state_schema_id
state_payload_or_reference
state_digest
representation_level
granularity_level
source_evidence_refs[]
transformation_lineage[]
proposed_action
proposed_action_digest
alternatives[]
uncertainty
confidence_calibration_ref
boundary_conditions[]
tail_risk_summary
out_of_distribution_status
reversibility_class
known_omissions[]
required_authoritative_correction
authoritative_correction_ref
created_at
expires_at
signature_or_attestation
```

The envelope is an evidence object.

It is not:

- truth;
- authority;
- approval;
- admissibility;
- clearance;
- a RACS decision;
- an execution permit.

A digest proves identity and integrity of the represented state. It does not prove that the state is complete, correct or sufficient.

## VAIG evaluation responsibilities

VAIG evaluates the actual produced envelope, not only the model profile admitted by MAL.

### Integrity and binding

VAIG checks:

- schema version and required fields;
- producer identity and attestation;
- model, runtime and MAL-clearance binding;
- action-case and workflow binding;
- state, history and proposed-action digests;
- expiry and freshness;
- transformation lineage.

### Evidence and state quality

VAIG checks:

- whether cited evidence supports the represented state;
- whether material evidence has been omitted;
- whether contradictions survive;
- whether alternatives are preserved;
- whether the history scope is sufficient and permitted;
- whether state compression removed a decision-relevant distinction;
- whether the representation is reproducible or behaviorally testable.

### Uncertainty and calibration

VAIG checks:

- uncertainty fields required by the output contract;
- calibration evidence;
- model-family or provider concentration;
- out-of-distribution indicators;
- self-review or correlated-review risk;
- unsupported confidence claims.

### Boundary and tail risk

VAIG checks:

- maximum-error exposure;
- high-percentile error;
- boundary cases;
- local discontinuities;
- rare but catastrophic transitions;
- cumulative multi-step consequence;
- reversibility and recovery cost;
- whether mean performance masks unacceptable tail risk.

### Representation and granularity consistency

The same action may appear as:

```text
agent step
→ tool call
→ workflow transition
→ transaction
→ organisational decision
→ external consequence
```

VAIG checks that a representation or granularity change has not:

- broadened scope;
- hidden a side effect;
- reduced consequence classification;
- removed authority-relevant context;
- split one high-risk action into many apparently low-risk calls;
- counted summaries as independent evidence;
- broken semantic and digest linkage.

Canonical rule:

> Governance is representation- and granularity-invariant, while remaining context- and consequence-sensitive.

### Authoritative correction

Where the MAL output contract or consequence profile requires authoritative correction, VAIG verifies that the named correction occurred and is appropriate.

Valid mechanisms may include:

- deterministic calculation;
- schema and invariant validation;
- system-of-record verification;
- formal model checking;
- independent human or model review;
- policy evaluation;
- current-state query;
- domain-specific authoritative solver;
- bounded simulation;
- exact postcondition check.

Another model opinion is not automatically an authoritative correction.

The proposing model cannot correct or attest itself as independent.

## VAIG result

VAIG emits a structured evaluation record linked to the rich state and exact proposed action.

Minimum conceptual fields:

```text
vaig_evaluation_id
rich_state_id
state_digest
history_digest
proposed_action_digest
mal_clearance_id
evidence_sufficiency
state_completeness
lineage_integrity
uncertainty_status
calibration_status
boundary_risk
tail_risk
out_of_distribution_status
granularity_consistency
authoritative_correction_status
surviving_alternatives[]
missing_information[]
reason_codes[]
recommended_outcome
conditions[]
created_at
expires_at
signature
```

The recommendation uses the canonical vocabulary:

```text
ALLOW
MODIFY
DEFER
STEP_UP
DENY
HALT
```

The VAIG result remains evaluation evidence. It does not create authority or execution clearance.

## REHT handoff

REHT receives:

```text
exact proposed action
+ VAIG evaluation
+ current mandate and authority
+ current policy
+ current target/system state
+ consequence model
+ correction result
```

REHT determines present admissibility and issues or withholds scoped clearance.

REHT must re-evaluate or refuse when:

- the proposed action digest changed;
- state or evidence expired;
- authority, policy, target or consequence state changed;
- required correction is absent or failed;
- representation compression hides a consequence-relevant distinction;
- a granularity change changes meaning or scope.

## MAL boundary

MAL admits the exact model, runtime and required output contract before invocation.

For rich-state workflows, MAL should bind:

```text
required_output_contract_id
required_state_schema_id
history_access_scope
approved_representation_levels[]
approved_granularity_levels[]
required_uncertainty_fields[]
required_boundary_metadata
required_tail_risk_metadata
required_provenance_fields[]
authoritative_correction_required
direct_scalar_output_allowed
state_digest_algorithm
```

MAL does not evaluate the actual produced envelope. That is VAIG's responsibility.

## RACS and Core boundary

RACS binds the evaluated state and REHT clearance to the exact action:

```text
rich_state_id
state_digest
history_digest
representation_level
granularity_level
vaig_evaluation_id
mal_clearance_id
proposed_action_digest
reht_clearance_id
conditions[]
expiry
replay_protection
```

Core verifies the binding and current preconditions at the effect boundary.

Core does not reinterpret the latent or represented state.

## Receipt requirements

The receipt chain should preserve:

```text
rich_state_id
state_schema_id
state_digest
history_scope
history_digest
representation_level
granularity_level
model/runtime/MAL binding
VAIG evaluation reference
REHT clearance reference
RACS decision and constraints
execution attestation
observed outcomes
```

Execution-time attestation and later observed outcome remain separate objects.

Veritas may preserve custody and outcome linkage. It does not evaluate, clear or create truth.

## Failure handling

| Condition | Required VAIG behavior |
|---|---|
| Missing required rich-state fields | `DEFER` or `DENY` according to policy |
| State or history digest mismatch | fail closed; `DENY` or `HALT` |
| Expired envelope | `DEFER` and require regeneration |
| Unsupported evidence references | mark insufficient; no consequential progression |
| Opaque state without evaluation basis | `STEP_UP`, `DEFER` or `DENY` |
| Unacceptable maximum/tail error | do not pass on mean score alone |
| Required correction absent | `DEFER` or `DENY` |
| Model self-review presented as independent correction | reject correction claim |
| Granularity change broadens scope | require new evaluation and clearance |
| Direct scalar output where rich state is mandatory | reject contract |

## Invariants

1. VAIG evaluates the actual state; MAL only admits the model/runtime/output profile.
2. A rich-state envelope cannot create authority.
3. A state digest proves identity, not truth or sufficiency.
4. The model cannot define or expand its own permitted history scope.
5. Direct scalar output cannot bypass a required rich-state contract.
6. Mean performance cannot override unacceptable tail or boundary risk.
7. Model self-review is not independent authoritative correction.
8. Representation changes preserve semantic, evidence and digest linkage.
9. Granularity changes cannot reduce consequence classification.
10. VAIG recommendation cannot directly reach a consequence-bearing adapter.
11. REHT clearance binds one exact action to one current evaluated state.
12. Core enforces the binding without reinterpreting the state.
13. Receipts preserve the state identity through execution and outcome observation.

## Required tests

- missing field and schema-version rejection;
- state/history/action digest tamper tests;
- stale envelope tests;
- unsupported evidence-reference tests;
- evidence omission and contradiction fixtures;
- state compression information-loss fixtures;
- mean-good/tail-bad rejection cases;
- out-of-distribution cases;
- self-review independence tests;
- split-action cumulative-consequence tests;
- cross-granularity semantic-consistency tests;
- required-correction absence and failure tests;
- changed action after evaluation tests;
- receipt state-binding and replay tests.

## Implementation status

| Item | Status |
|---|---|
| Architecture contract | Specified here |
| `RichStateEnvelopeV1` JSON schema | Required |
| VAIG evaluation schema extension | Required |
| MAL rich-state profile extension | Required in Index / model governance contracts |
| REHT handoff binding | Required |
| RACS receipt and decision binding | Required |
| Runtime implementation | Not authorized by this document alone |
| Tail and granularity benchmark suite | Required |

## No new governance universe

Do not create:

- a neural-operator governance layer;
- a model-issued clearance;
- a parallel admissibility engine;
- a separate receipt chain;
- a generic correction oracle;
- a latent-state truth claim;
- a new decision vocabulary.

Use the existing architecture:

```text
MAL admits
→ Harness orchestrates
→ model proposes
→ VAIG evaluates
→ REHT clears
→ RACS binds
→ Core enforces
→ Receipts attest
```
