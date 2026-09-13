# Misplaced Tofoo theory cleanup — 2026-06-14

Purpose: document why `Tofoo/theory` does not belong in the VAIG implementation repository.

---

## Finding

The VAIG repository contained exploratory Tofoo / Phi-law / LIM theory notes under:

```text
Tofoo/theory/
```

Files found:

```text
Tofoo/theory/2026-06-14-k-idempotens-5211.txt
Tofoo/theory/2026-06-14-k-simulering-arkitektur-vs-universal.txt
Tofoo/theory/2026-06-14-swarm-governance-coherent-ai.txt
Tofoo/theory/2026-06-14-worm-log-forensic-bevis.txt
```

These are theory / research-roadmap notes, not VAIG runtime implementation files.

---

## Correct home

Canonical destination:

```text
nsolland/Tofoo-/theory/
```

The files have been copied there before removal from VAIG.

---

## Boundary rule

VAIG should contain:

- runtime code;
- governance adapters;
- tests;
- implementation docs;
- audit/WORM implementation notes;
- product/runtime architecture.

Tofoo should contain:

- Phi-law theory;
- LIM theory;
- symbolic/theoretical framing;
- constants/falsification-roadmap work;
- theory notes;
- books/manuscripts.

---

## Do not delete source-of-truth material

This cleanup removes misplaced duplicates from VAIG only after preserving them in Tofoo.

Do not treat this as permission to delete theory notes from Tofoo.

---

## Private IP reminder

VAIG and Tofoo are private repositories. Internal theory, constants, formulas, tests, unpublished results and calibration notes must not be copied to public repositories or external surfaces without explicit owner approval.
