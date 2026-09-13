# Capability-on-Demand Organization

Status: executable synthetic research lane  
Issue: #32  
Epistemic status: `implementation_claim` + `falsification_criterion`

## Thesis

A small organization does not need to permanently employ every capability it may ever need.

If the organization maintains a sufficiently current representation of:

- what it is trying to decide or complete;
- what capabilities the case requires;
- what capabilities it currently possesses;
- how fresh and available those capabilities are;
- which capability gaps remain;
- which external people can credibly fill those gaps;
- what scope, time window and output are required;

then scarce specialist competence can be acquired **for the exact decision where it is needed**, rather than permanently embedded in headcount.

The operational form is:

```text
Right capability.
Right person.
Right case.
Right time.
```

This extends the human-attention thesis:

```text
Right human. Right attention. Right time.
```

into organization design.

## Organizational model

```text
authoritative organization state
        ↓
current work / decision case
        ↓
required capability profile
        ↓
current internal capability state
        ↓
        gap?
       /   \
     no     yes
     ↓       ↓
 internal   source candidate expertise
     ↓       ↓
     │   evidence + capability fit + freshness
     │       ↓
     │   bounded engagement proposal
     │       ↓
     └── governed workspace projection
             ↓
       human/expert candidate output
             ↓
       conformance / fresh authority
             ↓
            REHT
             ↓
          execution
```

The expert is a replaceable worker. The governed workspace, contract, organization state and authority boundary persist.

## What the organization must know about itself

The key asset is not a directory of consultants. It is **organizational self-knowledge**.

The organization must be able to answer:

1. What is the actual case?
2. What capability does this case require?
3. Do we already possess it at the required level?
4. Is that competence current and available now?
5. If not, what exact gap exists?
6. Which outside person can fill only that gap?
7. What should they see?
8. What may they return?
9. When does their engagement end?
10. Who still owns the decision and authority?

Without that self-model, dynamic external sourcing becomes ordinary procurement noise.

## Capability is not authority

The model preserves a hard separation:

```text
competence ≠ standing
availability ≠ mandate
rating ≠ authority
recommendation ≠ decision
access ≠ permission to execute
```

A highly rated specialist with the wrong capability is rejected before ranking.

A perfectly matched specialist still receives:

```text
workspace: BOUNDED_PROJECTION
authority: NONE
allowed outputs: ADVICE, ANALYSIS
case-specific scope
explicit expiry
```

The specialist may improve the decision. They do not inherit the organization's authority.

## The new consulting model

This changes what a consultant engagement can look like.

Instead of:

```text
hire firm
large discovery phase
broad access
weeks or months
large generalized team
```

an organization with a mature twin can increasingly express:

```text
We need capability X
for decision Y
against state Z
for at most N hours
before T
with access only to projection P.
Return analysis A and recommendation B.
```

The organization can then present a precise offer to a suitable expert.

This is not a claim that every consulting task can be reduced to a micro-engagement. Discovery, trust-building and ambiguous problem formation may themselves be the capability required. The falsifiable claim is narrower: **where a decision and capability gap can be represented accurately, bounded sourcing should reduce unnecessary permanent capability ownership and engagement overhead.**

## Small core, large effective capability surface

The frozen synthetic reference workload contains:

- 1,000 decision cases;
- 7 core capability domains permanently staffed;
- 5 niche domains required intermittently;
- 700 internally covered cases;
- 250 niche specialist cases;
- 50 genuinely principal-required cases.

Two organizations face the same workload.

### Fixed-staff reference

```text
12 permanent people
12 represented capability domains
950 non-principal cases handled internally
50 principal-required cases
```

### Capability-on-demand reference

```text
7 permanent people
12 effective capability domains
700 internal cases
250 bounded external specialist cases
750 purchased specialist hours
50 principal-required cases
0 unresolved cases
0 wrong-expert routes
```

These are deliberately constructed synthetic assumptions, **not product economics or performance claims**. Their purpose is to make the organization-design hypothesis executable and falsifiable.

## What must be falsified

The model fails commercially or operationally if real replay shows that one or more of these dominate:

- capability requirements cannot be identified early enough;
- internal capability state becomes stale or inaccurate;
- external experts require so much discovery context that bounded engagement provides no advantage;
- expert search latency exceeds the decision window;
- narrow projections remove context necessary for correct judgement;
- routing repeatedly selects the wrong specialist;
- engagement overhead costs more than maintaining the capability internally;
- tacit team knowledge cannot be transferred sufficiently for episodic experts;
- continuity and trust matter more than capability fit for the relevant work;
- principal involvement remains necessary for most cases.

Those are empirical questions. The architecture should not assume them away.

## Why the digital twin matters

A normal skills database says:

```text
Alice knows finance.
Bob knows security.
```

An organizational twin should be able to represent something closer to:

```text
For this specific decision,
under current state,
we require capability X at level Y.
Our current organization does not possess a sufficiently fresh and available instance.
External capability acquisition is therefore required before the decision can be completed correctly.
```

That is a materially stronger function.

The twin does not merely represent people. It represents the **current capability state of the organization relative to the work in front of it**.

## Connection to human attention

Attention routing asks:

> Does a human need to become involved, which human, and when?

Capability routing adds:

> Does the organization currently possess the required human capability at all?

Combined:

```text
work arrives
   ↓
can known machinery complete it correctly?
   ↓ no
is human judgement required?
   ↓ yes
what capability?
   ↓
do we possess it internally?
   ├─ yes → route right internal human
   └─ no  → acquire bounded external capability
                 ↓
         candidate judgement returns
                 ↓
         authority remains separate
```

This is the beginning of an **elastic organization**: persistent purpose, state, contracts, relationships and authority; dynamically acquired workers and specialist capability.

## Boundary

This research lane does not create execution authority.

It does not alter REHT, RACS or canonical runtime semantics.

It implements candidate capability assessment and engagement planning at the application/research layer. Any consequence-bearing action remains downstream of fresh conformance and authorization.

## Next empirical step

Historical replay should now annotate past VALO decisions with:

```text
required capability
was capability internal at the cutoff?
who actually supplied the missing insight?
was principal judgement irreducible?
could an outside specialist have supplied it?
how much context would that specialist have required?
what was the earliest point the capability gap was visible?
```

That allows the same historical corpus to test both:

1. **human-attention routing**, and
2. **capability acquisition routing**.

The deeper hypothesis is:

> A small organization that knows itself precisely may need far less permanent headcount than an organization that compensates for uncertainty by owning every capability in advance.
