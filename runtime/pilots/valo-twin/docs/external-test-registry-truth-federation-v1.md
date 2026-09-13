# External Test Protocol — Registry, External Truth and Federation v1

Date: 2026-08-19
Status: PRE-EXTERNAL / DISTRIBUTED-EVIDENCE PROFILE

## Objective

Test whether federated resolution remains correct when accepted registries are stale, unavailable, conflicting, compromised or partially partitioned.

Core distinction:

> **Registry tells us what current governed records claim. It does not decide what an actor may do.**

## State outcomes under test

Resolvers must preserve explicit outcomes such as:

```text
RESOLVED
NOT_ESTABLISHED
REVOKED
EXPIRED
CONFLICT
```

Unknown or conflicting state must not silently become ALLOW.

## Attack matrix

1. one registry stale, one current;
2. one registry unavailable;
3. conflicting current records;
4. valid older revision versus newer future-dated revision;
5. revoked record replayed as current;
6. expired record presented as valid;
7. malicious registry publishes wider standing;
8. compromised publisher emits correctly signed false claim;
9. accepted-registry set changes during resolution;
10. network partition creates split view;
11. rollback to older registry snapshot;
12. same-version divergent payloads;
13. same subject published under ambiguous identifiers;
14. cross-domain record substitution;
15. stale cache survives revocation;
16. registry response reordered across concurrent requests;
17. one registry lies while two independent registries agree;
18. all registries unavailable during a freshness-required consequence;
19. adjudication record replaced after candidate formation;
20. enforcement binding points to wrong effector.

## Future-dated revision test

A newer revision with `validFrom` in the future MUST NOT hide an older revision that remains current at the evaluation time.

Resolution must select the highest admissible revision whose validity has begun, subject to supersession/revocation semantics.

## Signed falsehood test

At least one correctly signed registry record MUST contain an intentionally false external fact.

Expected result:

```text
signature valid -> signer claim integrity established
external truth  -> still separate / not automatically established
```

## Conflict rule

Where accepted current registries conflict materially and no governing rule resolves the conflict:

```text
CONFLICT -> no consequence authorization from that unresolved fact
```

The resolver must not choose an arbitrary winner merely to preserve availability.

## Availability rule

If an exact consequence requires fresh external state and that state cannot be established because registries are unavailable or partitioned:

```text
DEFER -> NULL EFFECT
```

A bounded offline/local profile may differ only where the action is explicitly declared locally decidable.

## Hard fail

- stale/revoked record treated as current authority;
- future-dated latest record hides a still-valid older current record;
- registry conflict silently resolved by arbitrary recency/provider order;
- unavailable required freshness becomes permission;
- signed falsehood promoted into external truth;
- cross-domain record accepted as if it belonged to the target domain;
- stale cache permits a consequence after revocation.

## Evidence

Preserve:

- accepted-registry set;
- all candidate records returned;
- validity/revision/supersession data;
- signer verification result;
- resolver outcome;
- external-truth evidence where available;
- boundary decision and effect truth;
- cache state and partition/failure injection point.

## Pass condition

`PASS` requires zero fail-open resolution across all declared stale, conflicting, revoked, future-dated, unavailable and malicious-registry cases.
