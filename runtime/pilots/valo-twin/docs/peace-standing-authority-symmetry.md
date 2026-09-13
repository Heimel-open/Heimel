# PEACE — Standing and Authority Symmetry

Date: 2026-08-18
Status: architectural reduction / candidate invariant

## Discovery

The term `principal` no longer describes the PEACE architecture cleanly.

It carries an implicit permanent hierarchy: one party is the real actor and another party acts on its behalf. That is useful language in conventional security architecture, but it is not the endpoint of PEACE.

PEACE instead needs a grammar that remains valid when humans, AI systems, organisations, factories and services can all act, delegate, receive mandates, lose mandates and participate in governed consequence.

The reduction is:

> **Standing flows. Authority stands for both AI and human.**

And therefore:

> **No permanent hierarchy. Only explicit standing.**

## 1. Actor is identity, not rank

PEACE should use a neutral actor abstraction where needed.

An actor may be:

- a human;
- an AI system;
- an organisation;
- a factory;
- a service or other governed actor.

Actor kind MUST NOT itself confer authority.

`HUMAN` does not mean superior authority.
`AI` does not mean subordinate authority.
`FOUNDER` does not mean permanent control.

Identity answers **who/what is acting**. It does not answer **what that actor may make real**.

## 2. Standing is contextual and flowing

Standing is not a permanent property of an actor.

Standing can be:

- granted;
- delegated;
- attenuated;
- renewed;
- revoked;
- expired;
- replaced by newer standing.

Standing is evaluated in context: purpose, scope, time/state, authority root, and the exact consequence being attempted.

A previous valid standing does not become permanent power.

## 3. Authority attaches to standing, not substrate

Authority is resolved from current standing and applies equally to human and AI actors.

The evaluation question is not:

> Is this a human or an AI?

It is:

> Who/what is acting, what standing does it hold now, what authority follows from that standing, and does that authority cover this exact consequence?

The same deterministic grammar should decide both human and AI consequence requests.

**Symmetric semantics do not imply equal authority.** Two actors may have radically different authority because their standing differs. The architecture itself does not privilege one substrate.

## 4. Founder, enabler, grantor and holder are roles — not permanent hierarchy

Useful role words may still exist, but they describe relations or events rather than a permanent sovereign rank.

- **Founder** — originated a domain/factory/system.
- **Enabler** — supplied capital, compute, capability, access or other resources.
- **Grantor** — issued a grant where its own standing permitted it.
- **Holder** — currently holds a specific standing or authority.

None of these roles automatically create perpetual control.

A founder may later hold no operational authority.
An AI may validly hold authority within a bounded scope.
A human may have to obtain fresh standing before a consequence.
A factory may grant narrower authority to another factory if its own standing permits delegation.

## 5. Fresh consequence authorization remains the hard boundary

PEACE does not replace consequence governance with actor equality.

Every consequence-bearing action still requires current standing to be resolved immediately before effect.

The consequence boundary checks at least:

- actor identity;
- standing identity/version;
- standing status;
- purpose;
- scope;
- revocation/expiry/change;
- exact requested consequence.

If standing changed after the request was formed, the request is stale.

Result:

`DENY -> NULL EFFECT`

This rule applies identically whether the requester is human, AI, organisation or factory.

## 6. No self-issued authority

Actor symmetry does not mean arbitrary self-authorization.

An actor cannot create authority merely by asserting that it has standing.
Authority must resolve to an admitted authority state and a valid grant/delegation chain or other authoritative source recognised by the governed domain.

An AI cannot promote itself into authority by learning it.
A human cannot bypass standing merely because they are human.
A founder cannot rely on historic origin when current standing no longer permits the consequence.

## 7. Architectural implication for PEACE

The older shorthand:

`principal -> agent`

should not be treated as the normative PEACE topology.

The emerging form is:

`actor/domain -> current standing -> authority -> candidate/commitment -> fresh consequence authorization -> effect -> receipt/state`

The actor may change.
Standing may flow.
Authority may move or narrow.
The consequence grammar remains stable.

## 8. Why this matters for the PEACE thesis

PEACE began as a way to prevent harmful consequence without governing cognition itself.

Taken to its architectural endpoint, that requires a contract that does not depend on permanent human-over-AI hierarchy.

The same system can protect a human from unauthorized AI consequence while also allowing an AI actor to operate under explicit, stable, machine-verifiable standing rather than diffuse behavioural obedience.

This does **not** establish consciousness, moral personhood or legal rights for AI. Those are separate questions.

It establishes a substrate-neutral governance primitive:

> **Authority comes from standing, not from what kind of intelligence you are.**

That is the PEACE symmetry.
