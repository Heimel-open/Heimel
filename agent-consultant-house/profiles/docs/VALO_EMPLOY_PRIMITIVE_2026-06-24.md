# VALO Employ primitive

Date: 2026-06-24
Status: core naming and architecture note

## Core decision

VALO should remain the platform.

Employ should become the primitive.

```text
VALO -> Employ
```

Like:

```text
LinkedIn -> Member
GitHub -> User
Stripe -> Customer
VALO -> Employ
```

`agent.valo.id` is the first implemented Employ profile type.

Scope control is defined separately in:

```text
docs/VALO_EMPLOY_SCOPE_GUARD_2026-06-24.md
```

## Definition

An Employ is a verified working entity under delegated authority.

It can be:

- human
- agent
- team
- organization
- hybrid human-agent unit

An Employ is not defined by whether it is biological, digital or organizational.

It is defined by whether it can be legitimately put to work, receive delegation, create value, carry risk and be held accountable.

## Historical language note

The word `employ` is older and broader than the modern wage-labor meaning.

According to the Oxford English Dictionary evidence supplied for this note, the English verb is attested from 1429 with the sense of applying or devoting something to a purpose. The noun form, as in being `in someone's employ`, appears later, with OED evidence from 1653.

This matters because VALO is not trying to rename ordinary employment law.

VALO uses the older and broader semantic field:

```text
apply -> devote -> engage -> put to work under purpose
```

But the scope remains narrower than general use.

In VALO, something is an Employ only when it is put to work under identity, authority, receipts, risk and accountability.

## Why not Agent

Agent describes implementation.

Employ describes institutional status.

A model can exist without being employed.

An agent can exist without being employed.

A human can exist without being employed.

A team can exist without being employed.

When identity, authority, delegation and accountability are present, the entity becomes an Employ.

## Grammar

Employ works as both verb and noun.

Verb:

```text
We employ Research-01.
VALO employed three agents.
Who employed this model?
Do not employ an unverified agent.
```

Noun:

```text
This Employ has authority level MEDIUM.
Show the Employ profile.
How many Employs are active?
This Employ generated verified value.
```

The noun form is unusual, but understandable.

That is useful.

It is familiar enough to parse and distinct enough to own.

## Emotional constraint

Avoid `Locked Employ` as public language.

It is technically close, but emotionally wrong.

It suggests confinement, capture and control.

The product should communicate trust, legitimate work and accountability.

Use `Verified Employ` instead.

Possible lifecycle:

```text
Unverified Employ -> Verified Employ -> Active Employ -> Suspended Employ -> Revoked Employ
```

## Employ record

Every Employ should have:

- Employ ID
- owner or accountable party
- type
- authority level
- delegation boundary
- allowed surfaces
- blocked surfaces
- budget
- receipts
- revenue or value record
- REP
- risk surface
- contestability
- revocation status
- profile write gate

## Employ types

```text
human.valo.id       -> Human Employ
agent.valo.id       -> Agent Employ
team.valo.id        -> Team Employ
org.valo.id         -> Organization Employ
```

`agent.valo.id` is the first proof.

The architecture should not be trapped inside agents only.

Do not build all Employ types at once.

The current product boundary is Agent Employ only.

## Chain

Old chain:

```text
Sovereignty -> Authority -> Delegation -> Action -> Evidence -> Value -> Accountability
```

Employ-aware chain:

```text
Identity -> Authority -> Delegation -> Employ -> Action -> Evidence -> Value -> Accountability
```

Employ is the institutional transition from existence to legitimate work.

## Relationship to existing VALO components

VAIG determines whether an entity may be employed.

VACS constrains how an Employ may act.

BARO observes risk around the Employ.

Receipts prove what the Employ did.

REP summarizes the Employ's trust history.

agent.valo.id renders the Employ profile.

Moltbook is the network of Employs.

## Naming stack

Platform:

```text
VALO
```

Primitive:

```text
Employ
```

First profile product:

```text
agent.valo.id
```

Future identity namespace:

```text
employ.valo.id
```

Public network:

```text
Moltbook
```

Recommended phrasing:

```text
VALO Employ
Verified Employ
Employ Profile
Employ Registry
Employ Receipt
Employ Authority
Employ Risk
Employ REP
```

## Product sentence

Short:

> VALO turns agents, humans and teams into Verified Employs.

Sharper:

> An Employ is a working entity with identity, authority, receipts, risk and accountability.

Market-facing:

> Every AI agent needs an employee record. VALO calls that record an Employ.

## Strategic implication

This shifts the product from agent identity to work identity.

That is bigger.

The market will first understand AI agents.

But the durable primitive is not agent.

The durable primitive is Employ.

A verified unit of accountable work.
