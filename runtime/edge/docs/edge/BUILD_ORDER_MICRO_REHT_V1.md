# Build Order: micro-REHT V1

Status: READY FOR REVIEW
Repository: `nsolland/valo-edge`
Canonical base: `4f418b5180490752ba3212dd47b87aad15dbd4cc`
Branch: `feat/micro-reht-v1`

## Boundary

micro-REHT is the deterministic authorization boundary immediately before local consequence. It consumes an exact action commitment, Local VAIG evidence and a signed offline authority envelope.

It does not interpret sensor data, run a model, enforce a device command or attest the physical result.

The included HMAC-SHA256 verifier is a deterministic reference profile for tests and constrained integration. Hardware-backed asymmetric keys, provisioning and rotation remain later deliveries.

## Delivered

- versioned signed offline authority envelope
- exact device and action scope
- exact physical write-set binding for register, tag, parameter and intended value
- required, typed, bounded and enumerated action parameters
- actor or agent identity plus device/cell identity binding
- firmware, runtime and optional model binding
- sensor-source and evidence-freshness requirements
- physical-state predicates and material pre-action state commitment
- safety/interlock state as evidence input, never as authority
- use, rate, energy, duration and value budgets
- bounded permits reserved against every applicable budget
- bounded validity window with expiry and revocation
- persistent nonce, mutation and sequence replay protection
- persistent HALT with explicit recovery attestation
- monotonic preservation of prior non-ALLOW outcomes
- model-free authorization when the envelope does not require a model
- state snapshots supporting restart-safe permit consumption
- separate authorization requirement for rollback, compensation and retry actions

## Physical recovery rule

A recovery proposal is authorized only for the exact committed device, action, parameters, write-set and pre-action state. Material state drift between proposal and execution invalidates the authorization and requires a fresh evaluation.

The original permit never implicitly authorizes rollback, compensation, retry or a second write. Each is a new consequence with a new proposal and micro-REHT decision.

## Acceptance gates

- unsigned or mutated authority cannot authorize
- proposal, evidence and authority digests must bind exactly
- exact device/cell identity, action parameters and physical write-set must bind exactly
- missing required evidence produces DEFER or DENY, never ALLOW
- contradictory evidence produces DENY
- invalid action, parameters, state, identity or software binding produces DENY
- material pre-action state drift before execution produces DENY or requires re-evaluation, never silent reuse of the permit
- expired or revoked authority produces DENY
- every issued permit reserves its full use, rate, energy and value budget
- replay and mutation remain blocked after engine restart
- HALT remains active after engine restart
- rollback, compensation and retry require independent authorization
- a prior DENY, DEFER, STEP_UP or HALT cannot be upgraded
- focused micro-REHT V1 tests pass before CI
