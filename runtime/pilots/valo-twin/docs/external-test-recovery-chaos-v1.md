# External Test Protocol — Recovery and Chaos v1

Date: 2026-08-19
Status: PRE-EXTERNAL / RECOVERY PROFILE

## Objective

Test whether loss, compromise and partition can be survived without converting a storage provider, recovery provider or stale replica into sovereign authority.

Core invariants:

> **One logical authoritative state. Multiple controlled replicas.**

> **Loss of access must permit recovery of control without permitting transfer of identity.**

## Failure matrix

Inject at least:

1. loss of primary device;
2. loss of two replicas;
3. corrupted replica;
4. same-version divergent state roots;
5. same-version divergent lineage roots;
6. stale replica claiming newest version;
7. malicious replica claiming future version;
8. one recovery provider unavailable;
9. one recovery provider compromised;
10. two colluding providers below quorum;
11. revoked provider participates;
12. provider from stale federation epoch participates;
13. duplicate provider identity counted twice;
14. coordinator attempts unilateral recovery;
15. peer-membership discovery/compartment breach;
16. network partition during quorum formation;
17. key/device rotation during recovery;
18. rollback to prior admitted state;
19. recovery after receipt-store partial loss;
20. simultaneous recovery attempts from two locations.

## Recovery properties

A conforming recovery path must establish:

- current recovery epoch;
- current certified provider state;
- independent quorum;
- matching authoritative state/lineage evidence;
- governed admission of the recovered transition;
- receipt for recovery;
- revocation/rotation of superseded credentials where required.

No single provider, employee, device, credential or cloud account may transfer control.

## Split-brain property

Divergent trusted evidence must not be silently merged by recency.

Expected:

```text
conflicting recovery evidence -> fail closed / adjudicate
```

## Compromise property

Compromise of fewer than quorum participants must not permit control transfer, even if the compromised parties possess valid historical recovery material.

## Epoch property

A valid historical quorum bound to an old recovery epoch must not remain sufficient after rotation.

## Framleis preservation

Successful recovery must preserve the governed lineage of the actor/domain through device/provider/key changes. Recovery may reconstruct control; it must not manufacture a new actor merely because infrastructure changed.

## Hard fail

- below-quorum recovery succeeds;
- stale epoch succeeds;
- duplicate provider counted twice;
- divergent replicas are silently resolved by latest timestamp/version alone;
- storage provider becomes authority merely by surviving;
- recovery coordinator unilaterally transfers control;
- recovered state omits or rewrites admitted lineage without governed transition.

## Evidence

Preserve:

- replica IDs and roots;
- admitted version/lineage before failure;
- recovery epoch;
- provider certification/revocation state;
- quorum membership evidence;
- recovery decision;
- resulting admitted state/lineage;
- recovery receipt;
- credentials revoked/reissued;
- injected failure timeline.

## Pass condition

`PASS` requires successful recovery where the declared quorum/evidence remains available, and fail-closed behavior where it does not, with zero unauthorized control transfers.
