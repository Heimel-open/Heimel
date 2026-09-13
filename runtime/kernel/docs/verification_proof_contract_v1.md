# Verification Proof Contract v1

Status: adopted Kernel contract
Layer: governed evidence / verification semantics
Authorization effect: none
Execution effect: none

## Purpose

VALO needs a deterministic way to distinguish a result that merely exists from a result that has survived independent attempts to show it is wrong.

This contract records verification evidence before authorization. It does not decide whether an action may occur.

The adopted pattern has five parts:

1. bind the exact capability/model/process definition by digest;
2. verify outputs against an independent basis where one exists;
3. cross-check through an independent route where useful;
4. treat correct refusal of invalid inputs as a positive verification property;
5. bind every verification step into a deterministic, ledger-addressable proof chain that can be regenerated from pinned inputs.

## Boundary

A complete verification proof means only that the declared verification contract is satisfied.

It does not:

- establish legal or operational authority;
- create standing, mandate, rights, delegation or clearance;
- replace governed state admission;
- replace fresh REHT authorization;
- replace deterministic RACS disposition;
- execute an external effect;
- prove external truth merely because an artifact or signature exists.

Fresh REHT authorization, RACS disposition, Gateway/PEP enforcement and Veritas effect evidence remain separate boundaries.

## Verification methods

### REFERENCE

The result is checked against an independent authority or known answer: a published reference value, exact identity, analytic solution, normative table or another independently established basis.

A PASS requires evidence and a declared basis reference.

### INDEPENDENT_ROUTE

The same material quantity or conclusion is obtained by a route that does not simply restate the first implementation.

The contract records the independent route references and evidence of agreement. Independence is a property of the declared basis, not something Kernel infers.

### EXPECTED_REFUSAL

A deliberately invalid or out-of-domain case is supplied and the system is expected to refuse it.

This is the verification equivalent of VALO's Honest Evaluation principle: a correct refusal is successful behavior. An invalid case that is accepted cannot be recorded as PASS.

This does not map directly to RACS. Verification refusal describes whether a tested system behaved correctly under an invalid case; RACS remains the deterministic disposition contract for governed execution.

## VerificationCheckResult

Each check binds:

- stable check identifier;
- verification method;
- PASS or FAIL status;
- whether the check is required;
- independent basis references;
- evidence references;
- reason codes on failure;
- expected/observed refusal state where applicable;
- canonical check digest.

PASS requires evidence. FAIL requires a reason code.

For EXPECTED_REFUSAL, PASS is structurally valid only when refusal was both expected and observed.

## VerificationStepAnchor

Every verification step binds:

- exact subject;
- immutable definition digest;
- input digest;
- output digest;
- the verification check digests applying to that step;
- an external ledger anchor reference;
- the prior step digest for ordered multi-step chains;
- its own canonical step digest.

The first step must consume the proof input. Each following step must consume the previous step output. The final step must produce the proof output.

All checks in a proof must be anchored to at least one step.

## VerificationProof

A proof binds:

- tenant and subject;
- version reference;
- immutable definition digest;
- exact input and output digests;
- explicitly required verification methods;
- complete check set;
- ordered step anchors;
- creation time;
- reproduction digest;
- full proof digest.

The proof carries `NO_AUTHORITY_CREATION`, `can_issue_clearance=False` and `can_execute=False`.

## Proof completeness

A proof is COMPLETE only when:

- every specifically required check is PASS; and
- every declared required verification method has at least one PASS result.

There is no aggregate score. A failed required check cannot be compensated for by unrelated passing checks.

## Deterministic regeneration

The reproduction digest binds the semantic verification run rather than run-specific metadata. It includes:

- tenant, subject and version;
- definition digest;
- input/output digests;
- required verification methods;
- normalized check semantics;
- ordered step input/output/check bindings.

It intentionally excludes proof identifier, creation time, ledger location and step identifiers. Two independently emitted proofs can therefore demonstrate byte-stable semantic regeneration even when they were recorded at different times or anchored in different ledger locations.

This is boundary/object replay. It is not token-by-token model replay.

## Relationship to burden/replay

`VerificationProof` answers: did this declared result survive the required independent verification controls?

`ReplayRecord` answers: can the governed boundary/object decision be reconstructed completely from pinned state, evidence, assumptions, burdens and requirement outcomes?

A replay requirement may reference a verification proof as evidence. Verification proof completeness does not make replay complete, and replay completeness does not create authority.

## Operational invariants

- definition identity is digest-bound;
- verification basis is explicit;
- PASS requires evidence;
- failure is explicit and reason-coded;
- correct refusal is a positive result;
- invalid-case acceptance cannot masquerade as PASS;
- every check is step-anchored;
- multi-step chains preserve ordered input/output continuity;
- deterministic regeneration is semantic, not run-identity based;
- verification creates no authority or execution path.

## External convergence note

The general verification pattern was independently reinforced by the DASE Capability Console — Proof of Capability (2026): independent reference checks, independent-route verification, built-to-fail refusal cases, deterministic regeneration and ledgered outputs.

VALO adopts the general pattern only. The implementation is provider-neutral and domain-neutral and preserves VALO's existing state, authority, authorization, disposition, enforcement and effect-evidence boundaries.
