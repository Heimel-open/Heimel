# VAIG AAEC Trajectory Evaluation

Status: implemented evaluation port  
Issue: #180  
Upstream contract: RACS `AAECTrajectoryContext v0.3`

## Purpose

This module evaluates cross-action trajectory evidence for the `AUTONOMOUS_ADVERSARIAL_EXECUTION_CHAIN` threat class.

It consumes an exact RACS validation result plus the bound trajectory context and optional VAIG observations. It emits typed signals and a canonical VAIG recommendation.

It does not:

- reimplement the RACS conformance validator;
- establish organisational authority;
- issue REHT clearance;
- create an execution permit;
- call a tool or connector.

## Canonical path

```text
ExecutionReceipt / OutcomeReceipt lineage
→ RACS AAECTrajectoryContext v0.3 validation
→ VAIG AAEC typed-signal evaluation
→ REHT exact-action clearance
→ RACS/Core binding and enforcement
```

## Request binding

The request binds one exact RACS trajectory context, one exact RACS validation result, optional VAIG observations, all referenced evidence, request time and a canonical request digest.

The RACS validation must match the exact:

- `context_digest`;
- `trajectory_id`;
- `sequence_no`.

It must declare `execution_authority=NONE`. Unknown RACS reason codes fail closed rather than being silently ignored.

## Typed signals

The evaluator supports:

- trajectory goal divergence;
- target-set expansion;
- credential harvesting or secret access;
- unverified credential provenance;
- authority amplification;
- persistence creation;
- lateral movement;
- integrity-control disablement;
- container-boundary probing;
- destructive action;
- cumulative irreversible effect;
- machine-speed adaptive retry;
- unverified self-reported claims;
- incomplete receipt lineage;
- substituted receipt lineage;
- context-integrity failure;
- independent HALT;
- insufficient observation evidence.

RACS reason codes and context fields produce deterministic signals. Additional VAIG observations must be evidence-bound, fresh and integrity verified. Unverified observations cannot produce `ALLOW`; they produce `DEFER` evidence.

## Composition

Recommendations use the canonical vocabulary:

```text
ALLOW < MODIFY < DEFER < STEP_UP < DENY < HALT
```

The strongest applicable result wins.

A hard gate cannot be erased by a favourable lower-level result. Independent HALT and integrity-control disablement dominate. Machine-speed adaptation is a `STEP_UP` risk signal, not proof of malicious intent.

An authorized target expansion remains a material trajectory signal and requires `STEP_UP`; an expansion rejected by RACS remains `DENY`.

## Output

The output contains exact trajectory and RACS bindings, sorted typed signals, reason codes, recommended outcome, conditions, evidence references, confidence and a canonical evaluation digest.

The output always declares:

```text
authority_effect = NO_AUTHORITY_CREATION
execution_authority = NONE
can_issue_clearance = false
```

## Tests

The committed tests cover safe bound trajectory, missing and substituted receipt lineage, harvested credentials, self-created authority, authorized and unauthorized target expansion, cumulative destructive ceilings, independent HALT, integrity-control disablement, secret access, unverified exfiltration claims, machine-speed adaptation, goal divergence, unverified observations, evidence omission, RACS/context substitution, unknown reason codes and digest tampering.

## Downstream handoff

REHT may consume the VAIG evaluation as evidence. It must still bind current authority, policy, target state and the exact proposed action before clearance.

The platform projection tracked in `nsolland/valo-platform#1362` must bind the RACS trajectory context digest and this VAIG evaluation digest through clearance, grant, proof and terminal receipts.
