# PEACE State Replication — Logical Authority, Replicas, Offline Use and Recovery

Date: 2026-08-19
Status: architectural extension / demonstrator contract

## Core rule

> One logical authoritative state. Multiple controlled replicas.

PEACE MUST NOT define sovereignty by the physical storage location of the newest bytes.

A phone, laptop, home node, cloud backup or storage provider may hold a replica. None becomes the authority root merely because it stores a copy or has the highest local version number.

The governed domain owns the state transition semantics. Replicas only carry admitted state and lineage.

## 1. Authoritative state is logical, not locational

The domain is represented by a logical authority state:

- `domainId`
- `admittedVersion`
- `admittedStateRoot`
- `lineageRoot`
- admitted transition history / correlation

Storage can move without changing the logical domain.

```text
logical PEACE state
  -> phone replica
  -> laptop replica
  -> home-node replica
  -> encrypted recovery replica
```

Operational dependency on one of these locations MUST NOT imply constitutional control by that location.

## 2. Sync admitted transitions, not arbitrary files

A local observation or edit is not authoritative merely because it happened on a trusted device.

The semantic path is:

```text
local change
  -> state-transition candidate
  -> validate against current admitted version/root
  -> fresh authority / standing check
  -> admit or deny/defer
  -> receipt + new lineage root
  -> replicate admitted result
```

The unit of synchronization is therefore an admitted state transition plus lineage, not a blind last-write-wins file merge.

## 3. No last-write-wins sovereignty

PEACE MUST reject or explicitly resolve:

- stale base versions;
- same-version divergent state roots;
- same-version divergent lineage roots;
- a replica claiming a version beyond accepted authority state;
- replayed transition identifiers.

> No replica becomes sovereign merely because it has the newest bytes.

Conflict is explicit. Silent merge is not a sovereignty mechanism.

## 4. Offline semantics

PEACE should remain useful offline, but offline use is constrained by what can be established locally.

A bounded state transition MAY be admitted offline when:

- its base version/root matches the local accepted authority state;
- authority is valid and fresh enough for the action;
- the action does not require external freshness or remote revocation state.

A material transition MUST `DEFER -> NULL EFFECT` when required freshness cannot be established while offline.

```text
offline + locally decidable + fresh enough -> may admit
offline + external freshness required       -> DEFER -> NULL EFFECT
```

This is authority-aware sync rather than ordinary data sync.

## 5. Replication

Once a transition is admitted, replicas may synchronize to the resulting:

- admitted version;
- admitted state root;
- lineage root.

The replica identity and storage provider remain unchanged. Synchronization does not promote the replica into the authority source.

## 6. Recovery

Recovery reconstructs the logical authority state; it does not elect a surviving storage provider as sovereign.

The demonstrator requires matching independent trusted recovery replicas. Production systems may use threshold cryptography, hardware anchors, offline backups, trusted custodians or other governed recovery mechanisms.

Recovery MUST fail closed when trusted evidence of the current admitted state and lineage conflicts.

After recovery, credentials/devices may be reissued or revoked while the domain remains Framleis.

## 7. Relationship to Framleis

Framleis is the governed persistence of the actor/domain through transformation.

State replication is one mechanism that supports Framleis, but Framleis is not reducible to storage replication.

```text
phone disappears
laptop disappears
cloud provider disappears
keys rotate
models change
compute moves

logical governed domain is reconstructed
-> actor/domain is Framleis
```

## 8. Demonstrator invariants

`peaceStateReplication.ts` encodes the following deterministic invariants:

1. state transition must bind to current `domainId + version + stateRoot`;
2. fresh authority is required for admission;
3. replay fails closed;
4. stale/divergent replicas do not win through recency;
5. required external freshness while offline defers;
6. locally decidable bounded offline transitions may proceed;
7. replica sync copies admitted state/lineage without moving authority;
8. recovery requires matching independent trusted replicas;
9. recovery conflict fails closed.

## Plain-language version

> Telefonen kan ryke. PC-en kan byttes. AI-en kan forsvinne. Minnet og den styrte staten din består.

The important question is not simply **where the bytes are stored**. It is:

> Who controls the state, which transitions are admitted, how conflicts are resolved, and whether the domain can be reconstructed without surrendering authority to a storage provider?
