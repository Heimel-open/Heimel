# AI-Assisted Authorship and Echo-Risk Policy

Date: 2026-07-11
Status: active provenance and authorship policy
Scope: VALO, VAIG, REHT, RACS, BARO, Speider, VALO Core, GEA, Ambient Overlay and related research artifacts

## Purpose

This policy prevents AI-assisted drafting, analysis and iteration from being mistaken for independent validation, independent authorship or independent evidence.

AI assistance can improve speed and structure. It can also create closed validation loops where an idea is reformulated, repeated and then perceived as externally confirmed even though the same underlying premise produced every version.

## Echo-risk pattern

The following pattern must not be treated as independent corroboration:

```text
originating idea
-> AI reformulation
-> AI critique based on the same premise
-> AI-generated paper, note or architecture
-> repeated citation inside the same project
-> perceived independent support
```

Repetition, polish, agreement across model runs or agreement across several models does not by itself establish correctness, novelty, ownership, implementation status or external validation.

## Required separation

Every material artifact must distinguish, where applicable:

1. concept origin
2. prose authorship
3. AI drafting or editing assistance
4. formal-model authorship
5. software implementation authorship
6. verification or test authorship
7. evidence source
8. external review
9. publication authorship
10. copyright ownership

These categories must not be collapsed into a single statement such as "developed jointly" unless the evidence supports joint development across the relevant category.

## Independent validation rule

The following are not independent validation:

- a second prompt to the same model
- a different model using the same supplied context
- AI-generated peer review based only on project-provided claims
- restatement in another document
- internal cross-citation
- repeated agreement in meeting notes drafted from the same source material

Independent validation requires a materially independent source, reviewer, dataset, method, implementation, experiment or formal check.

## Contribution and ownership rule

AI assistance does not acquire authorship or ownership. Human contribution boundaries must still be documented precisely.

Co-authorship of a paper does not automatically establish joint ownership of every underlying contribution. Formal models, code, test assets, diagrams, prose, domain semantics and infrastructure descriptions must be classified separately.

The MECHA paper provides a concrete precedent:

- the publication is jointly authored
- Charles R. Rupp retains the EFA framework semantics, MECHA tuple, HSRS, Empty Cockpit doctrine and related domain definitions
- Njål Gaute Solland retains the TLA+ specification, model-checking implementation, verification results and VALO infrastructure descriptions
- DOI: `10.5281/zenodo.20668225`

## Evidence labels

Every significant claim should carry one of the following statuses:

- `owner_statement`
- `project_record`
- `implemented`
- `tested`
- `formally_checked`
- `externally_validated`
- `published`
- `third_party_reference`
- `historical_collaboration`
- `unresolved`

AI-generated analysis without external evidence must not be labeled `externally_validated`.

## Repository requirements

For new architecture, research and IP files:

- identify the human originator
- identify AI assistance where material
- link primary evidence
- separate proposal from implementation
- separate implementation from verification
- separate internal review from external review
- register third-party frameworks and copied material
- preserve Git history

## Review trigger

A provenance review is required when:

- the same claim appears across several project files without a primary source
- AI-generated text is cited as support for another AI-generated text
- authorship language becomes broader over time
- collaboration references appear as active runtime dependencies without implementation evidence
- a polished narrative exceeds the underlying technical evidence
- ownership of a formal model, codebase or standard is unclear

## Core principle

AI may assist expression.

AI repetition is not evidence.

Authorship, ownership, implementation and validation must remain independently traceable.
