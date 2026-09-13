# relAIon ↔ Dyade adapter

## Status

Dyade is a **read-only external continuity/context window** for relAIon.

It is not the relAIon individual, not Alpha, not canonical memory, and not local lineage.

## Invariants

- access ≠ identity
- reading ≠ memory
- external continuation ≠ local lineage
- external reasoning ≠ the individual
- imported Dyade material enters as RAW observation evidence
- no Dyade import may directly mutate canonical relAIon state
- no execution path is introduced by this adapter
- promotion into durable state requires the normal relAIon evidence/admissibility path

## Flow

```text
Dyade continuation
  session
  lineage
  head
  events
      ↓
DyadeAdapter (read-only)
      ↓
ObservationEnvelope(stage=RAW)
      ↓
relAIon provenance / admissibility / evidence handling
      ↓
possible later local learning or state change
```

The adapter preserves external provenance at minimum:

- provider
- adapter version
- session id
- lineage
- head
- event payloads
- ingestion time through the observation envelope

The adapter deliberately does **not** interpret Dyade content as truth. It only exposes a governed, provenance-bearing view into an external continuation.

## Alpha relationship

Alpha may read Dyade through this adapter and use the resulting evidence as part of its environment/history.

That does not make Alpha a Dyade continuation.

Alpha retains its own identity, lineage, developmental trajectory, continuity state and causal history.
