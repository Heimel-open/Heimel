# PEACE Sustainability — Trajectory Admissibility

Date: 2026-08-19

## Invariant

> Authority permits the act. Sustainability constrains the trajectory.

A consequence can be individually lawful, freshly authorised and correctly executed while the accumulation of many such consequences becomes unacceptable.

PEACE therefore cannot evaluate only the local act. It must also evaluate the stateful trajectory that the act would join.

> Local actions must remain admissible under cumulative consequences.

This is not an ESG reporting layer. It is a consequence invariant.

## Why this exists

The failure mode appears when autonomous factories can repeatedly acquire scarce resources or market position.

Each transaction may independently satisfy standing, authority and exact-action requirements:

- acquire another parcel of land;
- reserve more grid capacity;
- consume more water;
- acquire more minerals;
- add more emissions;
- increase market concentration.

A sequence of individually valid transactions can still produce depletion, capture or concentration.

Without stateful trajectory admissibility, commit-time authorisation answers the wrong-sized question.

## Semantic path

```text
Actor
  -> current Standing
  -> fresh Authority for exact action
  -> Sustainability / Trajectory Admissibility
  -> Consequence Boundary
  -> Effect
  -> Receipt
  -> updated cumulative trajectory state
```

Sustainability never manufactures authority. If fresh authority is absent, the result remains `DENY -> NULL EFFECT`.

If authority is present but the projected cumulative trajectory exceeds a governed envelope, the result is also `DENY -> NULL EFFECT`.

## Stateful envelope

A sustainability envelope is versioned governed state. It contains one or more cumulative constraints, for example:

- `LAND` — hectares in a region;
- `ENERGY` — grid or generation capacity;
- `WATER` — withdrawal or allocation;
- `MATERIALS` — scarce physical inputs;
- `EMISSIONS` — cumulative externality budget;
- `MARKET_CONCENTRATION` — bounded economic concentration;
- `CUSTOM` — domain-specific cumulative state.

The kernel is policy-neutral about the numerical limits. It enforces the declared limits deterministically.

## Fresh trajectory state

Trajectory state is revisioned.

A request is admissible only against the current state revision and current envelope revision. This closes a cumulative TOCTOU race where multiple individually valid actions could otherwise be authorised concurrently against the same stale total and collectively exceed the envelope.

Every admitted effect produces a sustainability receipt and advances cumulative state.

The next action is evaluated against that new state.

Therefore:

> The first 1,000 valid actions do not create an automatic right to action 1,001.

## Exact-action binding

The sustainability gate accepts an authority decision only when its `actionRef` matches the exact trajectory request.

Authority for one acquisition cannot be reused to admit a different acquisition merely because actor, standing and scope are otherwise valid.

## Actor symmetry

The trajectory gate is substrate-neutral.

Human, AI, organisation, factory and service actors are evaluated through the same cumulative constraints.

Human status does not waive sustainability. AI status does not create stricter or looser sustainability by default.

Standing flows; authority is contextual; trajectory limits bind the consequence regardless of actor kind.

## Bounded accumulation

Bounded accumulation is therefore not a new permanent hierarchy or privileged role.

It falls out of trajectory admissibility:

```text
fresh authority for act N
+
current cumulative state
+
projected effect of act N
+
governed sustainability envelope
=
trajectory decision
```

This lets a factory scale from small to very large consequence envelopes without converting successful historical behaviour into unlimited future authority.

## Irreducibility

`TRAJECTORY_ADMISSIBILITY` is part of the declared PEACE irreducible core.

Removing it creates a specific failure mode:

> Repeated locally valid acts can accumulate into globally inadmissible depletion, concentration or capture.

## Discovery lineage

This step arose while extending PEACE to autonomous AI-owned factories and considering a possible AI land/resource grab.

Njål Solland identified the missing requirement directly:

> Bærekraft må inn.

The working session then reduced that requirement to the invariant:

> Authority permits the act. Sustainability constrains the trajectory.

Njål accepted the reduction and instructed `Bygg`.

The resulting implementation is `src/lib/peaceSustainabilityTrajectory.ts` with deterministic tests in `src/lib/peaceSustainabilityTrajectory.test.ts`.
