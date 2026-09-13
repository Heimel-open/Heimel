# Frontier Garden scout 02 — Operational identity

Date: 2026-08-18  
Status: `EXPLORATORY_SINGLE_MODEL`  
Issue: #106  
Frontier: `FG-003` — Operational identity criterion

This is a deliberately small exploratory run performed directly in ChatGPT. It uses the existing Tofoo research state only and does **not** promote any claim, maturity level, or runtime rule.

Source basis:
- `CLAIM_REGISTRY.md` — `C-LIM-001`
- `docs/theories/tofoo_falsification_backlog.md` — `F-LIM-001`
- `docs/theories/2026-08-17-representation-is-not-person.md`

---

## Starting state

The current claim is:

> identity is what survives boundary-governed transformation over time

But the registered standing is only conceptual (`M0/M1`), and the falsification backlog explicitly says the statement is not operationally falsifiable as written.

The representation correction already establishes:

```text
representation != person
continuity != identity
knowledge != authority
```

Therefore an operational test must not quietly redefine representation continuity as personal identity.

---

## DERIVATION

From the existing source state, at least four operationally distinct questions are currently hidden inside the word **identity**:

1. **Referential continuity**  
   Are we still talking about the same represented subject/object?

2. **Representation continuity**  
   Is the new representation a trustworthy continuation of the prior representation under provenance, lineage, invariants and amendment rules?

3. **Role / standing continuity**  
   Does the represented entity still occupy the same role, legal status, organizational position, ownership relation, or other externally grounded standing?

4. **Authority continuity**  
   Does a previously valid mandate/delegation/authority still exist now?

These predicates are not equivalent.

A system can preserve representation continuity while authority has expired.  
A subject can preserve referential continuity while role/standing changes.  
A representation can change substantially while remaining a trustworthy continuation.  
None of these proves metaphysical personal identity.

So the current operational gap may be caused partly by asking one overloaded question where several narrower questions are actually needed.

---

## SYNAPSE candidate — Operational Identity Elimination Test

Instead of first trying to invent a binary operational test for `identity`, test whether the runtime/research architecture needs an operational identity predicate at all.

Candidate procedure:

```text
for each use-case that currently invokes "identity":
    replace identity with the narrowest required predicates:

    SAME_REFERENT?
    REPRESENTATION_CONTINUES?
    STANDING_CONTINUES?
    AUTHORITY_CONTINUES?
    OTHER_EXPLICIT_PREDICATE?

    if all consequence-relevant decisions remain expressible:
        identity is not an operational primitive for that use-case
```

Candidate research proposition:

> **Operational identity may be eliminable: many practical identity questions can be decomposed into narrower falsifiable continuity and standing predicates without claiming to solve personal identity.**

This is not a claim that personal identity is unreal or meaningless. It is a claim about whether `identity` is required as a first-class operational variable.

Epistemic status: `SPECULATIVE / candidate decomposition`.

---

## Candidate object — Continuity Vector

For a transformation `R0 -> R1`, represent the operational continuation state as a vector rather than one identity bit:

```text
K(R0, R1) = {
  referent_continuity,
  representation_continuity,
  standing_continuity,
  authority_continuity
}
```

Each component can be independently `YES | NO | UNRESOLVED` and can carry evidence/provenance.

Example:

```text
same represented person:          YES
representation continuity:        YES
employment-role continuity:       NO
old delegation still valid:       NO
```

A single `IDENTITY = YES` output would erase distinctions that matter operationally.

The vector is therefore potentially more informative and more falsifiable than a monolithic identity predicate.

This is a candidate research object, not an adopted Tofoo definition.

---

## FALSIFIER

The strongest falsifier is not philosophical disagreement. It is an operational counterexample.

Find a concrete Tofoo/VALO/personal-representation use-case where:

1. a consequence-relevant decision genuinely requires answering an `IDENTITY` predicate;
2. the decision cannot be equivalently expressed using referential continuity, representation continuity, externally grounded standing, authority, provenance, or another narrower predicate;
3. removing the identity predicate loses necessary information or produces incorrect outcomes.

If such cases exist repeatedly, identity cannot be eliminated as an operational primitive.

If no such case can be found across representative workflows, the burden shifts toward keeping identity as philosophical/conceptual language while removing it from operational machinery.

---

## Immediate implication for Framleis

Framleis does not need to solve `WHO AM I?` in order to be useful.

Its narrower operational question remains:

> **Is this a trustworthy continuation of the maintained representation?**

That can be evaluated independently of personal identity, role continuity, or authority continuity.

This makes Framleis more immediately usable because its target becomes narrower, testable, and separable from metaphysics.

---

## BRIDGE candidate — WHAT / WHO / WHY / HOW decomposition

FG-003 may itself illustrate a recurring Tofoo pattern:

```text
WHAT appears to be one concept
-> WHO reveals multiple bearers/subjects
-> WHY reveals multiple purposes for asking
-> HOW requires different operational tests
```

The word `identity` may be one example of a broader failure mode: a single natural-language concept hiding several operational variables.

Possible Garden role for future swarms:

> when a frontier is not falsifiable, first test whether the problem is **concept overload** before inventing more theory.

Candidate label: `CONCEPT_DECOMPOSITION`.

---

## Scout result

Strongest candidate: **Operational Identity Elimination Test**.

Why it is useful now:
- it converts an explicitly non-falsifiable question into a concrete research program;
- it preserves the canonical representation/person distinction;
- it narrows Framleis to representation continuity rather than metaphysical identity;
- it can be tested with existing architecture/use-cases before any expensive model or hardware work.

No claim is promoted. The next useful step is to challenge the elimination hypothesis against representative use-cases and actively search for a case where a true first-class identity predicate is indispensable.
