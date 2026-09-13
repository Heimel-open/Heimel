# VALO Employ scope guard

Date: 2026-06-24
Status: scope control note

## Why this exists

Employ is a strong primitive because it can stretch across humans, agents, teams and organizations.

That is also the risk.

If Employ means everything, it becomes nothing.

The purpose of this note is to keep the concept from overflowing.

## Etymology fit

The word `employ` carries two useful meanings:

- to use, apply or devote something to a purpose
- to engage someone in work

The historical record supports this broader range. OED evidence supplied for this note places the English verb in 1429 with the sense of applying or devoting something to a purpose, while the noun form appears later, with evidence from 1653.

That makes the word suitable for VALO.

VALO does not merely run an agent.

VALO folds an entity into legitimate work.

But this etymology must not be used to widen the product into every kind of use, tool, workflow or resource allocation.

The older meaning gives conceptual permission.

The architecture gives the boundary.

## Narrow definition

An Employ is:

```text
A verified working entity under delegated authority.
```

It must have:

- identity
- accountable owner or responsible party
- delegated authority
- allowed surfaces
- blocked surfaces
- receipts
- risk surface
- accountability path
- revocation path

If these are missing, it is not an Employ.

It is only a tool, model, bot, workflow, user, team or organization.

## What is not an Employ

Not every model is an Employ.

Not every automation is an Employ.

Not every user is an Employ.

Not every API key is an Employ.

Not every software service is an Employ.

Not every digital twin is an Employ.

Not every agent is an Employ.

The boundary is delegated accountable work.

## Scope rule

Use Employ only when the entity can answer these questions:

```text
Who is it?
Who is accountable for it?
What is it allowed to do?
What is it forbidden to do?
What has it done?
What receipts prove it?
What risk does it carry?
How can authority be revoked?
```

If the system cannot answer these questions, do not call it an Employ.

## Build boundary

Do not build all Employ types now.

Current implemented type:

```text
Agent Employ
```

Current implementation:

```text
agent.valo.id
```

Explicitly out of scope for current prototype:

- Human Employ UI
- Team Employ UI
- Organization Employ UI
- full Moltbook feed
- marketplace
- payment rails
- employment law semantics
- HR system replacement
- legal worker classification

The prototype proves the primitive through one type only:

```text
Agent Employ -> research-01.agent.valo.id
```

## Product containment

Current product:

```text
Verified Agent Employ Profile
```

Current buyer promise:

```text
We can give your AI agent a verifiable work record with authority, receipts, risk and accountability.
```

Do not sell:

```text
We replace HR.
We replace ERP.
We create a full agent economy.
We solve employment law for AI.
We are building all digital work identity.
```

Those may be long-term implications.

They are not the first product.

## Correct ladder

Build in this order:

```text
1. One Agent Employ profile
2. Three Agent Employ profiles
3. Employ Registry
4. profile.json and proof.json
5. static bucket
6. read-only API
7. MCP verifier
8. receipt-backed feed
9. marketplace
10. broader Employ types
```

Do not jump from step 1 to step 10.

## Naming guard

Use now:

```text
VALO Employ
Verified Employ
Agent Employ
Employ Profile
Employ Registry
Employ Receipt
Employ Authority
```

Avoid now:

```text
Locked Employ
AI employee
employment system
HR for agents
universal digital twin network
full economic operating system
```

These phrases create emotional, legal or scope problems too early.

## Scope sentence

The safe sentence is:

> VALO Employ is a verified work identity for entities that act under delegated authority.

The first implementation is:

> agent.valo.id, a verified Employ profile for AI agents.

The future vision is:

> Moltbook, a network of Employs where discovery and reward are based on receipts rather than attention.

## Final guardrail

Employ is not the whole company.

Employ is the object.

VALO is the system.

agent.valo.id is the first product.

Moltbook is the later network.

Keep them separate or the architecture will overflow.
