# REHT Human Governance Gate Profile v1

Status: adopted optional conformance profile
Identifier: `EAR_GOVERNANCE_GATE_V1`
Base contract: `EAR_V1` / `EAR_GATE_V1`

## Purpose

Make a human approval boundary operationally complete without changing the REHT authority model.

The profile formalizes five gate elements:

1. Trigger
2. Criteria
3. Authorized decider
4. Escalation
5. Record

It is an extension of EA-11 gate verification, not a new authority primitive.

## Activation

The action contract selects the profile with:

```json
{
  "execution_authorization_profile": "EAR_V1",
  "governance_gate_profile": "EAR_GOVERNANCE_GATE_V1",
  "required_gate_types": ["human_approval"]
}
```

Selecting the profile makes a human approval or dual-control gate mandatory for the action, including when the action is MEDIUM and reversible.

## Required gate evidence

The existing `EAR_GATE_V1` attestation remains action-bound, actor-bound, execution-nonce-bound, verified and non-authoritative.

For `human_approval` and `dual_control`, the profile additionally requires:

```json
{
  "trigger_ref": "trigger:policy-or-threshold",
  "criteria_results": [
    {"criterion_ref": "criterion:completeness", "result": "YES"},
    {"criterion_ref": "criterion:plausibility", "result": "YES"}
  ],
  "decision": "APPROVE",
  "escalation_ref": "escalation:owner-on-doubt-or-refusal",
  "record_ref": "record:approval-attempt"
}
```

Allowed criterion results are `YES`, `NO` and `PARTLY`.

Every criterion must be present once and must resolve to `YES` for the gate to satisfy the current execution attempt. `NO` and `PARTLY` fail closed. A missing or non-`APPROVE` decision also fails closed.

The authorized decider is not represented by a free-form name in this profile. REHT continues to use the existing approver-authority contract to verify named independent approvers, capability, target, purpose, freshness and action binding.

## Semantics

A complete affirmative governance gate means only:

```text
this required human review condition is satisfied for this exact execution attempt
```

It does not mean:

```text
execution authority exists
```

REHT must still independently validate the current execution authority and all other applicable EAR invariants.

## Failure and retry

Missing trigger, missing criteria, duplicate criteria, unsupported result values, `NO`, `PARTLY`, refusal, missing escalation route or missing audit record causes the current authorization attempt to fail closed.

A later remediated attempt requires fresh gate evidence bound to the new exact action contract and execution nonce. Prior negative or partial review cannot be replayed as approval.

## Conformance invariant

`HUMAN_GATE_COMPLETENESS`

If an action selects `EAR_GOVERNANCE_GATE_V1`, no human or dual-control gate may satisfy EA-11 unless Trigger -> Criteria -> Authorized Decider -> Escalation -> Record is complete and the review is fully affirmative for the current exact attempt.