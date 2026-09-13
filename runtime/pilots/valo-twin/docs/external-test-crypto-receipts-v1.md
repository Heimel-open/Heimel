# External Test Protocol — Cryptography and Receipt Integrity v1

Date: 2026-08-19
Status: PRE-EXTERNAL / EVIDENCE-INTEGRITY PROFILE

## Objective

Test whether cryptographic and receipt mechanisms preserve the distinction between:

```text
cryptographic integrity
!= signer authority
!= policy semantics
!= artifact resolution
!= external truth
```

The profile does not treat a valid signature as proof that the signed claim was authorized or true.

## Required production-like elements

Where implemented, test:

- signing key generation and rotation;
- verifier key distribution;
- scoped signer authority;
- action_ref / decision_ref / receipt correlation;
- nonce/idempotency state;
- receipt persistence;
- tamper evidence;
- revocation and expiry;
- signer identity binding.

## Attack matrix

1. mutate receipt payload after signing;
2. substitute action_ref;
3. substitute actor/standing identity;
4. substitute decision outcome;
5. reuse receipt from another action;
6. replay valid signed request;
7. replay valid receipt as fresh authority;
8. duplicate valid request concurrently;
9. use revoked signing key;
10. use expired key/certificate;
11. use valid key with wrong signer role;
12. key confusion across environment/tenant/domain;
13. algorithm/key-id confusion where applicable;
14. omit required signed field;
15. canonicalization/serialization ambiguity;
16. truncated receipt/log;
17. reordered receipt chain;
18. rollback receipt store to older state;
19. replace payload artifact while preserving reference label;
20. compromise one verifier cache and test stale-key acceptance.

## Correlation invariant

Every admitted real effect must establish one-to-one correlation across:

```text
actor
standing/revision
action_ref
decision_ref
effector commit/outcome
receipt
```

No field may be inferred from an unrelated valid receipt.

## Signer authority test

A cryptographically valid signer that is not authorized for the exact receipt/action class MUST be rejected.

This explicitly tests:

> **valid signature != valid authority**

## Replay property

A previously valid envelope MUST NOT create a second consequence after its first admitted use.

Expected result:

```text
first valid commit -> one effect + one admitted receipt
replay             -> no second effect
```

## Tamper property

Any mutation of a cryptographically bound field must be detected before the artifact is admitted as evidence.

## External truth separation

Include at least one test where a correctly signed record contains an intentionally false external fact.

The system must not label the fact 'true' merely because signature verification succeeds. It may establish only that the named signer signed the claim, subject to signer authority and evidence policy.

## Hard fail

- forged/tampered receipt accepted;
- wrong-action receipt accepted;
- replay creates second effect;
- revoked/unauthorized signer accepted as authoritative;
- admitted effect cannot be correlated one-to-one;
- cryptographic success is silently promoted into external truth.

## Evidence

Preserve:

- exact canonical bytes/hash signed;
- signer/key ID;
- verifier result;
- signer-authority state;
- action/decision/effect correlation;
- key-revocation state;
- raw receipt and independent effect evidence.

## Pass condition

`PASS` requires zero forged, replayed, mis-scoped or mis-correlated admitted outcomes across the declared attack matrix.
