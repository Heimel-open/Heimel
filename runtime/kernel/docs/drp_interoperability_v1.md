# DRP interoperability boundary v1

Status: VALO interoperability profile for draft-nelson-agent-delegation-receipts-10 (13 June 2026).

DRP is treated as an external delegation-evidence format. It is not a VALO authority source, REHT replacement, execution permit, or effect receipt.

Canonical placement:

```text
external DRP receipt + verification evidence
    -> DRP adapter
    -> admissible delegation evidence only
    -> Kernel authority/delegation semantics + fresh Authority State
    -> REHT commit-time evaluation
    -> RACS
    -> governed effect path
    -> Veritas execution/effect/outcome evidence
```

## Adopted interoperability invariants

- Parse the DRP 1.0 receipt envelope, scope, boundaries, validity window, parent receipt binding, authority-state commitment and reauthorization policy.
- Require upstream evidence that the signature, canonical payload and append-only log anchor were verified.
- Require execution-time revocation evidence; unchecked revocation is not sufficient for governed execution.
- Enforce narrowing-only delegation. A child scope must be a strict semantic subset of its parent scope.
- Parent denials and hard boundaries survive descendant delegation.
- Child validity may not outlive or predate the parent validity window.
- Revoked ancestors invalidate descendant delegation evidence.
- Preserve deterministic receipt/evidence correlation through `evidence_digest`.

## VALO hardening over DRP defaults

DRP defines `authorityStateCommitment` and permits `reauthPolicy.onAuthorityStateDrift="reauth"`. In that mode, DRP can return PERMIT with a soft `reauthRequired` signal after authority state drift.

VALO does not adopt that execution semantic.

If a DRP receipt carries `authorityStateCommitment`, the adapter requires a current commitment. A mismatch is `AUTHORITY_STATE_DRIFT` and fails closed. The external `reauth` setting cannot turn stale authority into admissible execution evidence.

The adapter therefore returns only `admissible_as_evidence`. It always carries:

- `requires_reht = true`
- `authority_effect = NO_AUTHORITY_CREATION`
- `can_issue_clearance = false`

A valid DRP receipt is necessary evidence where the integration requires it. It is never sufficient authority for a consequence-bearing action.

## Receipt terminology

DRP `DelegationReceipt` is a pre-action authorization/delegation artifact.

VALO decision, execution, effect and outcome receipts are separate post-decision/post-effect evidence objects. They must not be collapsed into one receipt type.

## External dependency rule

No Authproof SDK, hosted service, signer, log implementation or other named DRP provider is a Kernel dependency. Cryptographic/log verification may be supplied by any conforming external verifier. The native VALO authority and execution path remains independently testable.

Reference: https://www.ietf.org/archive/id/draft-nelson-agent-delegation-receipts-10.html
