# Phi-law consistency audit — 2026-06-14

Purpose: identify inconsistencies across README, manifesto and books before editing source material.

This is an audit note, not a rewrite.

---

## Files read

```text
context.md
README.md
Phi-Law-Validation/PHI_LAW_MANIFESTO.md
Bøker/The_Eukaryotic_Transition_in_AI_Bok2.txt
Bøker/Phi_Neste_Setning_Bok3.txt
```

Full-book line-by-line review is not complete. Findings below are limited to the sections read.

---

## Summary

The core law is present, but consistency drift exists across:

- number of domains: 125 vs 128;
- LIM version: V5.2 badge vs V5.3 manifesto;
- protocols: README says five predictions, manifesto says P1-P6, context says P1-P9 and P10 next;
- four axioms: explicit in manifesto, not surfaced in README or books;
- constants: README uses C0/alpha/tau, context adds rho/gamma/delta/zeta/Goldilocks dimensionless form;
- claim maturity: claims mix symbolic, formal, simulated and empirical status.

Recommended approach: do not rewrite books yet. First create canonical reference files and then patch front matter / README references.

---

## Finding 1 — Domain count drift

Observed:

- README badge says `128 domener`.
- Manifesto front matter says `Konsiliens: Bekreftet i 128 domener`.
- Manifesto section heading says `KONSILIENS: 125 DOMENER`.

Risk:

Readers will suspect careless inflation or version drift.

Recommended fix:

Create one canonical domain registry:

```text
Phi-Law-Validation/domain_registry.md
```

Then patch README and manifesto to reference the registry count.

Do not manually maintain numbers in multiple places.

Suggested canonical wording until registry is counted:

```text
Konsiliens: domain registry maintained in Phi-Law-Validation/domain_registry.md
```

If the correct count is 128, update the manifesto heading from 125 to 128 after verifying the table count.

---

## Finding 2 — LIM version drift

Observed:

- README badge says LIM V5.2.
- Manifesto title says LIM V5.3.
- README structure comment says `PHI_LAW_MANIFESTO.md ← LIM V5.2 — full syntese`.

Risk:

Version uncertainty weakens the artifact.

Recommended fix:

Create:

```text
Phi-Law-Validation/version.md
```

with current canonical version and changelog.

Patch README badge and structure comment after version is confirmed.

Likely current canonical version: `LIM V5.3` because the manifesto title says so.

---

## Finding 3 — Four axioms not propagated

Observed:

Manifesto explicitly defines four axioms:

```text
A1 — Identitet
A2 — Skapelse
A3 — Tid
A4 — Rom
```

README does not show the four axioms. Bok 2 foregrounds Lovgiveren/Tolken and admissibility. Bok 3 foregrounds identity/filter and human decision, but the four-axiom set is not visible in the early front matter sections read.

Risk:

The law may appear to change form depending on entry point.

Recommended fix:

Create canonical axiom file:

```text
Phi-Law-Validation/axioms.md
```

Then reference it from:

- README.md
- PHI_LAW_MANIFESTO.md
- Bok 2 front matter or appendix
- Bok 3 appendix or protocol section

Do not force the full axiom block into every book chapter. Use references or appendices to preserve voice.

---

## Finding 4 — Protocol count drift

Observed:

- README says five falsifiable predictions.
- Manifesto section says P1-P6.
- Context says P1-P9 complete and P10 next.

Risk:

The validation program appears inconsistent.

Recommended fix:

Create canonical experiment registry:

```text
Phi-Law-Validation/experiment_registry.md
```

Fields:

```text
Protocol
Status
Claim maturity
Artifact path
Result summary
Falsification condition
```

Then patch README and manifesto to refer to that file.

---

## Finding 5 — Constants drift / multiple normalizations

Observed:

README and manifesto use:

```text
C0 = 4495.27 bits
alpha = 0.42
tau = [1888, 4766]
```

Context adds:

```text
rho = gamma/(delta-4) = 0.8625437492
Goldilocks dimensionless = [e^(-gamma), 1/zeta3] = [0.5615, 0.8319]
tau = r_eff/r_max in [0,1]
```

Risk:

A reader may think there are competing tau definitions.

Recommended fix:

Create canonical constants file:

```text
Phi-Law-Validation/constants.md
```

It should separate:

1. historical VALO OS constants;
2. dimensionless tau normalization;
3. model/substrate-specific C0 calibration;
4. open questions.

Do not erase old constants; mark their role.

---

## Finding 6 — Claim status needs maturity labels

Observed:

Some passages say:

```text
Teoretisk bevist
Empirisk falsifiserbar
Bekreftet i 128 domener
```

Context now defines claim maturity labels M0-M6.

Risk:

External readers may conflate symbolic truth, formal proof, simulation and replication.

Recommended fix:

Add claim maturity labels to:

- experiment registry;
- constants file;
- domain registry;
- manifesto executive summary.

Example:

```text
P1: M3 Simulated / M4 working-system run, not independently replicated.
P6: M2 Formal / bounded model check.
Domain list: M1 conceptual consilience unless directly evidenced.
```

---

## Finding 7 — Tofoo/VALO bridge is now present but not referenced from README

Observed:

`context.md` now contains the bridge:

```text
Tofoo = meaning
Φ-loven = theory
LIM = principle
VAIG = implementation
VALO L1 = enforcement
Janus/WORM = evidence
ACS = standard
```

But README does not yet expose this bridge clearly.

Recommended fix:

Add a short section to README after `Hva er Φ-loven?`:

```text
Fra Tofoo til VALO
Tofoo bærer språket. LIM er prinsippet. VAIG er runtime-laget. VALO L1 er håndhevingen. Janus/WORM er beviset. ACS er standardiseringsveien.
```

---

## Recommended safe patch order

1. Create `Phi-Law-Validation/axioms.md`.
2. Create `Phi-Law-Validation/constants.md`.
3. Create `Phi-Law-Validation/experiment_registry.md`.
4. Create `Phi-Law-Validation/domain_registry.md`.
5. Patch README to reference these four canonical files.
6. Patch PHI_LAW_MANIFESTO.md headings/version/counts only after registries are in place.
7. Do not rewrite books until source-of-truth files are stable.

---

## Do not do yet

- Do not rewrite Bok 1, Bok 2 or Bok 3.
- Do not change the voice.
- Do not remove strong claims; classify them first.
- Do not manually change 125 to 128 without counting the domain registry.
- Do not merge old C0/tau and new dimensionless tau without a constants note.

---

## Next action

Create the four canonical reference files first.

Then patch README and manifesto with references, not broad rewrites.
