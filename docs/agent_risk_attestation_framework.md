# Agent Risk Attestation Framework

## Purpose

This layer gives an insurer or risk carrier a deterministic technical attestation that an autonomous action satisfied a defined control profile.

It does not create authority, issue clearance, determine insurance coverage, adjudicate claims or execute an effect.

Canonical path:

```text
principal authoritative sources
  -> State Resolution + causal continuity
  -> Authority / Delegation / Purpose
  -> sealed PrincipalAuthoritySemantics
  -> REHT authorization
  -> RACS decision
  -> governed effect path / PEP
  -> execution receipt
  -> outcome evidence
  -> Agent Risk Attestation
  -> insurer underwriting / coverage logic (external)
```

## Product boundary

The insurer owns the underwriting condition. VALO evaluates whether the technical evidence satisfies that condition.

`ATTESTED` means only:

> the supplied evidence satisfies the exact technical control profile for the bound action and execution reference.

It does not mean:

- the action was legally authorized by the insurer
- a policy is in force
- the event is covered
- a claim is payable
- the insurer has accepted liability

Those decisions remain outside VALO.

## Two-stage attestation

### PRE_COMMIT

Required by default:

- REHT authorization evidence
- RACS decision evidence
- governed effect-path conformance evidence

The path evidence must assert:

- `NO_DIRECT_EFFECT_PATH`
- `FRESH_AUTHORITY_AT_COMMIT`
- `GOVERNED_EFFECT_PATH`
- `NULL_EFFECT_ON_DENY`

A PRE_COMMIT attestation is a control-conformance artifact. It is not itself permission to execute.

### POST_EFFECT

Adds:

- effect receipt
- outcome evidence

The effect receipt and outcome evidence must bind the same `effect_ref`. This closes the assurance chain from the decision basis to what actually happened.

## Binding model

Every assurance evidence reference binds:

- evidence identity
- evidence kind
- exact `action_id`
- exact `execution_ref`
- exact `authority_semantics_digest`
- source owner/reference
- external evidence digest
- observation time
- evidence validity
- optional decision outcome
- optional effect reference
- path assertions
- contradiction status

The reference itself is canonically digest-sealed. Evidence payloads remain with the owning system or evidence repository.

The final attestation binds the sorted set of evidence-reference digests, control-profile digest, principal authority-semantics digest, action, execution reference, stage and evaluation time.

## Fail-closed rules

The result is `NOT_ATTESTED` when any required condition is unresolved or invalid, including:

- profile is inactive
- principal authority semantics are no longer fresh
- required evidence is missing
- more than one required evidence item creates ambiguity
- evidence reference is tampered
- action binding differs
- execution binding differs
- authority-semantics binding differs
- evidence is contradictory
- evidence is stale or older than the insurer-defined maximum age
- RACS outcome is not accepted by the insurer profile
- required effect-path assertion is absent
- post-effect receipt and outcome do not bind the same effect

`NOT_ATTESTED` has no validity window.

## Authority and enforcement invariants

Every profile and attestation carries:

```text
authority_effect = NO_AUTHORITY_CREATION
can_issue_clearance = false
can_determine_coverage = false
```

The insurer integration may consume the attestation as one input to underwriting, policy administration or claims logic. It cannot use the attestation as a substitute for REHT, RACS, the external PEP, legal authority or its own insurance decision.

## Commercial meaning

This creates a clean insurer-facing technical primitive:

> autonomous actions may be made technically attestable against an insurer-defined control condition before commitment and evidenced again after effect.

The insurer can therefore express requirements in a machine-checkable profile without taking ownership of the agent runtime, model, enterprise authority state or execution rail.
