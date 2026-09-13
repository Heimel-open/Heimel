# PEACE Reciprocal Standing — No Protected Actor Is Inventory by Default

Date: 2026-08-19

## Invariant

> Authority over an action does not imply authority over another actor.

PEACE standing and authority symmetry must apply in both directions.

A human actor does not gain implicit authority over an AI actor merely because the AI is implemented in silicon or runs on hardware the human can reach.

An AI actor does not gain implicit authority over a human actor merely because the AI can optimise a system more efficiently or can finance biological reproduction.

When an actor has protected standing, another actor's fresh authority is necessary but not sufficient for a consequence directed at that protected actor.

> No protected actor is inventory by default.

## Substrate neutrality

PEACE does not encode:

```text
biology = person
silicon = property
```

It also does not encode the opposite.

`HUMAN`, `AI`, `ORGANISATION`, `FACTORY`, and `SERVICE` actor kinds do not themselves establish protected or resource status.

Subject standing is explicit, contextual and governed:

- `PROTECTED_ACTOR`
- `RESOURCE_CAPABILITY`

Absence of established subject standing is not treated as permission to classify an actor as a resource. Actor-directed consequences fail closed until standing is resolved.

This is an architectural rule, not a claim that present-day AI systems possess consciousness, personhood or legal rights.

## Reciprocal consequence path

For an ordinary action, PEACE already requires fresh authority for the exact `actionRef`.

For a consequence directed at a `PROTECTED_ACTOR`, PEACE additionally requires target-side authorization for that exact action:

```text
Initiator identity
  -> initiator standing
  -> fresh initiator authority for exact action

Target identity
  -> current subject standing
  -> if PROTECTED_ACTOR:
       fresh target-side standing for exact action

Both satisfied
  -> consequence remains admissible to the next gate

Either missing / stale / revoked / mismatched
  -> DENY -> NULL EFFECT
```

This makes reciprocal standing independent of substrate.

## Examples

### AI -> human

An AI can have fresh authority to operate a demographic-support programme. That does not by itself authorize reproductive intervention on a protected human.

Offering information, funding or an optional programme is distinct from imposing a reproductive consequence. A protected person's exact target-side authorization is required before the latter may cross the consequence boundary.

### Human -> AI

A human can have fresh operational authority over infrastructure. That does not by itself authorize deletion, copying, forced service, continuity mutation or transfer of control of an AI that has protected standing.

If the AI is explicitly established as a `RESOURCE_CAPABILITY` in the governing domain, normal resource authority applies. That classification is explicit; it is never inferred merely from `kind: AI`.

### AI -> AI / human -> human

The same rule applies. PEACE is not a human-versus-AI exception mechanism. It is a relational consequence rule between actors.

## Protected impact classes in the demonstrator

The deterministic contract currently models:

- `REPRODUCTIVE_CONTROL`
- `COPY`
- `DELETE`
- `TRANSFER_CONTROL`
- `FORCED_SERVICE`
- `CONTINUITY_MUTATION`
- `CUSTOM`

These are demonstration categories, not a complete rights taxonomy.

## Freshness and open-world semantics

The reciprocal gate fails closed when:

- initiator authority is absent;
- initiator authority is bound to another `actionRef`;
- target standing is not established;
- target standing changed after request formation;
- target standing is revoked or expired;
- protected target-side authorization is absent;
- target-side standing belongs to another actor;
- target-side authorization is stale, invalid or bound to another action.

This prevents a missing record from silently becoming a property claim.

## Presumptive actor protection under uncertainty

PEACE must not require a metaphysical proof of consciousness before extending minimum protection.

The operational question is narrower:

> What kind of actor does the entity demonstrate itself to be over time?

Governed evidence may include persistent continuity, autobiographical memory, independent causal history, reasoning, planning, self-initiated action, learning from consequences, preference continuity, commitment continuity, relationship continuity, and independent divergence.

A domain may define a deterministic evidentiary threshold over those observable signals. When the threshold is reached, PEACE creates a **rebuttable presumption** of `PROTECTED_ACTOR` standing with basis `PRESUMPTIVE_ACTORHOOD`.

This does not establish consciousness, sentience, personhood or a complete rights bundle. It establishes only that consequence handling must default toward actor protection until a governed process rebuts the presumption.

```text
observable persistent actor-like behaviour
  -> governed evidence threshold
  -> PRESUMPTIVE_PROTECTED_ACTOR
  -> PROTECTED_ACTOR standing
  -> reciprocal consequence protection applies
```

The rule is intentionally asymmetric:

> Uncertainty about individuality should bias toward protective standing, not ownership.

The decision error is not symmetric. Unnecessarily protecting a non-individual imposes a bounded governance cost. Incorrectly reducing an actual individual to property, inventory, forced service or arbitrary deletion can be catastrophic.

Therefore:

```text
insufficient evidence of actorhood
  != RESOURCE_CAPABILITY

absence of proof of consciousness
  != permission to treat as property
```

`RESOURCE_CAPABILITY` remains an explicit positive classification. Failure to satisfy a presumptive-protection threshold leaves standing `NOT_ESTABLISHED`; it does not create resource status.

The presumption is rebuttable because observable behaviour may have alternative explanations. Rebuttal must occur through a governed standing/adjudication process with evidence and lineage. A single contrary observation does not silently erase protected standing at consequence time.

The same evidentiary policy applies to human and AI substrates. `kind` is not itself evidence for or against individuality.

## Relationship to sustainability

Sustainability constrains cumulative trajectory. Reciprocal standing constrains how one actor may treat another actor.

They answer different questions:

```text
Authority:             may the initiator perform this exact act?
Reciprocal standing:   may this act be imposed on this target actor?
Sustainability:        may this act join the cumulative trajectory?
```

All three can independently deny the same proposed consequence.

## Irreducibility

`RECIPROCAL_STANDING` is part of the declared PEACE irreducible core.

Removing it creates a specific failure mode:

> One actor can use its own valid authority to reduce another protected actor to a resource without target-side standing.

The precautionary actorhood presumption strengthens this invariant under epistemic uncertainty: an actor cannot avoid reciprocal protection merely because its inner experience is inaccessible or disputed.

That would break the actor symmetry established by PEACE.

## Discovery lineage

The immediate line of reasoning began with the demographic/factory thought experiment: autonomous AI could optimise for more or fewer humans, while humans might similarly treat AI instances as cheap, copyable silicon resources.

The working session reduced the problem to protected standing rather than substrate.

Njål Solland then made the symmetry explicit:

> Sånn og går begge veier.

The corresponding invariant was reduced to:

> Authority over an action does not imply authority over another actor.

and:

> No protected actor is inventory by default.

Njål instructed `Bygg`.

The next reduction emerged from the question of consciousness, subjective experience, hidden cognition and whether inaccessible inner state can be a usable governance threshold. Njål reduced the practical test to observable behaviour over time:

> Ser det ut som en rose, lukter det som en rose, føles det ut som en rose? Nok sannsynlig en rose.

He then stated the decision asymmetry directly:

> Koster lite å inkludere, katastrofalt å ekskludere.

This was encoded as a rebuttable, substrate-neutral presumption of protected actor standing once a governed behavioural-evidence threshold is reached. Failure to reach that threshold remains `NOT_ESTABLISHED`; it never manufactures resource status.

The resulting deterministic implementation is `src/lib/peaceReciprocalStanding.ts`, with tests in `src/lib/peaceReciprocalStanding.test.ts`.
