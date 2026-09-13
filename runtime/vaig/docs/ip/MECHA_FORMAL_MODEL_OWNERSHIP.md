# MECHA Formal Model — Ownership and Contribution Boundary

Date: 2026-07-11
Status: active provenance record

## Classification

The MECHA paper is a jointly authored publication.

The formal model contained in and accompanying the paper is classified separately as:

`solland_owned_contribution_in_joint_artifact`

## Controlling publication record

Title: `MECHA: Formal Verification of Conjunctive Human-AI Execution Governance Using TLA+`

Version: `1.2`

Date: `2026-06-12`

Zenodo DOI: `10.5281/zenodo.20668225`

License: `CC BY 4.0`

## Explicit author-contribution boundary

The paper states that Charles R. Rupp developed:

- MECHA tuple semantics
- HSRS framework
- Empty Cockpit doctrine
- governance invariants
- manuscript draft

The paper states that Njål Gaute Solland developed:

- the TLA+ specification
- the model-checking implementation
- the verification process and results
- validation of the safety properties
- production implementation context
- integration of the verification results into the final manuscript

## Explicit copyright boundary

The paper states that each author retains copyright in their respective contributions.

Accordingly:

- Charles R. Rupp retains copyright in EFA framework semantics, the MECHA tuple, HSRS, Empty Cockpit doctrine and related domain definitions.
- Njål Gaute Solland retains copyright in the TLA+ specification, model-checking implementation, verification results and VALO infrastructure descriptions.
- The integrated paper remains a jointly attributed publication.

## Required interpretation

Publication co-authorship does not create joint ownership of every underlying contribution.

The repository must distinguish between:

- co-authorship of the integrated paper
- ownership of MECHA and EFA semantics
- ownership of the TLA+ formal specification
- ownership of the model-checking implementation
- ownership of verification evidence and results
- ownership of VALO infrastructure and implementation descriptions

No joint ownership of the TLA+ formal model may be inferred solely from joint authorship of the paper.

## Repository treatment

The TLA+ formal model, model-checking assets, verification results and VALO implementation context may be described as Solland-created and VALO-owned contributions, subject to the CC BY 4.0 terms that apply to the published integrated paper.

References to Charles Rupp, MECHA or EFA must not be represented as ownership claims over:

- the TLA+ specification created by Solland
- the model-checking implementation
- the verification results
- Rust or other implementations derived from Solland's formal model
- VALO Core, VAIG or other independently developed VALO infrastructure

## Preservation

The joint publication record and dual attribution must remain intact.

This record does not alter the paper's authorship. It records the narrower ownership boundary explicitly stated in the publication itself.