# Ownership Clarification Log

Date: 2026-07-11
Source: project conversation log
Status: owner clarification record

## Statement

Njål Gaute Solland clarified that:

- GEA is his / VALO-owned work.
- Ambient Overlay is his / VALO-owned work.
- The MECHA formal model was created by him and is his contribution.
- The ownership and contribution boundary for the formal model is explicitly defined in the deposited Zenodo paper.

The clarification was made while reviewing traces of Charles Rupp / MECHA-related language across active VALO repositories.

## Interpretation

This statement means:

1. GEA must be treated as VALO-owned architecture.
2. Ambient Overlay must be treated as VALO-owned architecture and product work.
3. The MECHA paper may be a joint publication while the formal model remains a separately attributable Solland-owned contribution.
4. Co-authorship of the paper must not be used to infer joint ownership of every underlying model, implementation or formal artifact.
5. References to Charles Rupp, MECHA, EFA or related collaboration concepts inside GEA or Ambient Overlay do not establish authorship, ownership or derivation of the underlying work.
6. Such references must be classified individually as one of:
   - external reference,
   - historical collaboration context,
   - integration language,
   - removable active dependency wording.
7. Any cleanup must preserve Git history and genuinely joint material with attribution.

## Operational consequence

GEA, Ambient Overlay and the Solland-created formal model are excluded from the category `unresolved ownership` unless later documentary evidence creates a specific conflict.

The MECHA publication and the formal model must be tracked separately:

- publication authorship: joint as stated in the paper
- formal-model contribution: Njål Gaute Solland, according to the owner's statement and the paper's deposited contribution/IP declaration

The cleanup task is limited to identifying and removing or reclassifying external collaboration references. It must not rewrite the origin of underlying VALO-owned or Solland-created work.

## Evidence handling

This file records the owner's explicit project instruction. The deposited Zenodo paper is identified by the owner as the controlling documentary source for the formal-model contribution and IP boundary.

The exact Zenodo record and wording should be linked or quoted into the repository when available. This internal record is not a substitute for signed assignment agreements, contributor agreements or legal advice.