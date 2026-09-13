# Personal Context Substrates v1

## Purpose

VALO distinguishes between personal context that a principal explicitly stores and a personal model that a system infers over time.

Both may improve reasoning and personalization. Neither becomes authoritative state or execution authority merely by existing.

Canonical classes:

```text
Explicit personal knowledge substrate
  e.g. Obsidian, files, notes, journals, curated references

Inferred personal-model substrate
  e.g. Honcho, learned preferences, behavioural patterns, relationship models
```

These are independent, hot-swappable substrates. VALO does not depend strategically on either provider or implementation.

## Canonical boundary

```text
Explicit personal knowledge ---------+
                                     |
Inferred personal model -------------+--> Personal Context Projection
                                           |
                                           v
                                    Governed Workspace
                                           |
                                     any worker/model
                                           |
                                  candidate output/state
                                           |
                              deterministic conformance
                                           |
                     +---------------------+--------------------+
                     |                                          |
            persistent-state candidate                     proposed action
                     |                                          |
             State Admission                              fresh Kernel state
                     |                                          |
              Kernel WorldState                         Authority State / scope
                                                                |
                                                               REHT
                                                                |
                                                               RACS
                                                                |
                                                               PEP
                                                                |
                                                            Veritas
```

The personal-context layer helps answer "what context should the system consider?" It does not answer "what is operative truth?" or "may this action be committed?"

## Explicit personal knowledge

An explicit personal knowledge substrate contains material the principal or an authorized process deliberately stores: notes, documents, links, preferences, plans, journals and structured records.

Obsidian is a canonical example of this class, not a dependency.

The storage location does not itself establish standing or authority. A note saying "I approve this payment" is not automatically a valid mandate. A copied policy is not automatically the current policy. A remembered fact is not automatically current operational state.

Explicit principal-authored content may be admissible evidence when its provenance, identity, standing, scope, purpose and freshness satisfy the relevant state-admission contract. The substrate itself never creates those properties.

Invariant:

> Principal-controlled storage can preserve an assertion; it cannot manufacture its standing.

## Inferred personal model

An inferred personal-model substrate builds representations from interactions and observations: likely preferences, recurring behaviour, relationships, habits, intent hypotheses, predictions and other learned characteristics.

Honcho is a canonical example of this class, not a dependency.

This information is useful for context selection, personalization, planning and candidate generation. It is inherently inferential unless separately resolved against admissible evidence and admitted state.

Invariant:

> A model of the principal is context about the principal, never authority for the principal.

Accordingly:

- inferred preference is not consent
- predicted intent is not delegation
- behavioural regularity is not mandate
- model confidence is not standing
- persistence is not identity
- relationship modelling is not authority to represent either party
- an inferred model may suggest an action but cannot authorize its consequence

This extends the principal/model separation defined in `docs/principal_authority_projection.md`.

## Personal Context Projection

Workers should receive a bounded projection rather than unrestricted access to all personal stores.

A projection should preserve at minimum:

- principal/tenant binding
- substrate class: `EXPLICIT_KNOWLEDGE` or `INFERRED_MODEL`
- provider/substrate identifier without provider-specific authority semantics
- provenance or source reference where available
- observation/update time
- explicit vs inferred status
- confidence only when meaningful for inferred material
- purpose and workspace scope
- admission status when material is already represented in Kernel state

The projection is context. It grants no rights, delegation or execution clearance.

## Promotion into governed state

Neither substrate mutates `WorldState` directly.

Material that must become persistent operative state follows the normal path:

```text
personal context
  -> state candidate
  -> provenance / identity / standing / contradiction checks
  -> deterministic State Admission
  -> explicit Kernel event
  -> maintained WorldState
```

The admission decision must be based on the source and its standing, not on the reputation or convenience of the storage/model provider.

An inference can remain `INFERRED`, be rejected, be quarantined, conflict with maintained state, or be superseded by stronger/current evidence. A personal model cannot promote its own inference to `CONFIRMED`.

## Execution boundary

A worker may use both explicit and inferred personal context to propose a consequence-bearing action.

Before commit, VALO resolves fresh authoritative state, authority, delegation, purpose and scope. REHT evaluates the proposed action at the consequence boundary. RACS returns the deterministic disposition. The PEP alone performs the governed effect.

Therefore:

```text
personal understanding != operative state
operative state          != authority
inferred intent           != permission
permission                != committed effect
```

Each boundary remains explicit.

## Provider neutrality

Obsidian and Honcho are implementation examples only.

Equivalent stores or models may be substituted without changing Kernel semantics, provided the adapter preserves the same trust classification and cannot widen standing or authority.

A provider adapter may:

- retrieve or project explicit content
- retrieve or project inferred representations
- preserve provenance metadata
- narrow or omit context under workspace policy

A provider adapter may not:

- mint identity or principal standing
- declare an inference authoritative
- create delegation, rights or mandate
- mutate Kernel state directly
- bypass State Admission
- issue REHT or RACS clearance
- execute external effects

This follows the VALO principle: the substrate is replaceable; governed state and correct delivery are not.

## Failure rules

Fail closed for authority-sensitive use when:

- principal/tenant binding is missing or ambiguous
- explicit and inferred material are not distinguishable
- provenance required by policy is absent
- context exceeds its permitted purpose or workspace scope
- material is stale where freshness is required
- an inferred representation is presented as authoritative state
- a substrate attempts to widen authority or delegation
- a worker relies on personal context instead of fresh authoritative state at commit time

Non-authoritative context may still be omitted or quarantined without blocking unrelated work when it is not required for the active action.

## Architectural consequence

VALO may combine a principal-controlled explicit knowledge substrate with an inferred personal-model substrate to create a richer personal AI without allowing either substrate to become the principal's authority layer.

The durable boundary is:

> know me deeply; act only within current, explicit authority.
