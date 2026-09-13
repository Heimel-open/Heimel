# Digital DNA

Your digital twin. Still you. Framleis.

Digital DNA is an executable research implementation of the Tofoo identity-continuity grammar:

- `S`: state space
- `T`: declared admissible transformation classes
- `~`: identity-equivalence relation
- `I`: protected invariants
- `C`: continuity-collapse conditions

The kernel answers one narrow question:

> Does this proposed digital-twin state remain a legitimate continuation of the represented identity?

It does not decide whether the state is true, authoritative, legally sufficient, admissible for execution, or permitted to cause an external effect.

## Core objects

`DigitalDNAManifest` carries the executable continuity contract: identity, state-space identifier, allowed transformation classes, equivalence rules, invariants, collapse conditions and amendment authorities.

`IdentityTransition` carries the before/after state, transformation class, evidence digests, memory references and any proposed protected amendment.

`ContinuityEvaluator` is deterministic and returns one of:

- `CONTINUES`
- `REVIEW_REQUIRED`
- `BREAK`
- `INDETERMINATE`

`ContinuityReceipt` hashes the manifest, transition, before/after states, distributed-memory root and prior receipt so continuity evaluations can form a reproducible lineage.

## Distributed memory

Digital DNA does not require all memory to live inside one twin. `MemoryRecord` is content-addressed and supports `ACTIVE`, `DORMANT`, `DISPUTED`, `SUPERSEDED` and `REVOKED` states. Superseded or revoked records retain predecessor lineage instead of silently disappearing.

## Protected amendment

Ordinary declared transformations can evolve state within the existing continuity contract. A protected amendment to the contract itself requires an explicitly authorized amender. The represented twin cannot silently redefine the rules by which it is judged to remain the same represented identity.

## Minimal example

```python
from digital_dna import (
    ContinuityEvaluator,
    DigitalDNAManifest,
    EquivalenceRule,
    IdentityTransition,
    StateOperator,
    StateRule,
)

manifest = DigitalDNAManifest(
    identity_id="person:123",
    version="1",
    state_space_id="personal-twin.v1",
    allowed_transformations=frozenset({"LEARN", "CORRECT"}),
    equivalence_rules=(EquivalenceRule("principal.id"),),
    invariants=(StateRule("principal.id", StateOperator.EQUAL, "person:123"),),
)

transition = IdentityTransition(
    transition_id="tx-1",
    transformation="LEARN",
    before_state={"principal": {"id": "person:123"}, "preference": "A"},
    after_state={"principal": {"id": "person:123"}, "preference": "B"},
    observed_at="2026-08-17T06:00:00Z",
)

result = ContinuityEvaluator().evaluate(manifest, transition)
assert result.decision.value == "CONTINUES"
```

Epistemic status: `implementation_claim`.

This remains informative Tofoo research code. It is not the runtime source of truth for VAIG, REHT, RACS or any execution authority.
