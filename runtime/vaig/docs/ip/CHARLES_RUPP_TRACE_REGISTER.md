# Charles Rupp / MECHA Trace Register

Date: 2026-07-11  
Status: active cleanup record  
Scope: VAIG and linked active architecture repositories

## Purpose

This register documents where collaboration-linked material appeared, what was removed from active architecture, what remains preserved as historical evidence, and why.

The objective is separation, not erasure.

## Classification rule

Each trace is classified as:

- `historical_joint_work`: explicitly co-authored or jointly developed material retained with attribution
- `external_reference`: cited research or framework that is not a runtime dependency
- `active_dependency_removed`: wording that incorrectly made collaboration-linked concepts appear structurally required
- `valo_owned_with_external_reference`: VALO-owned work containing external or historical references
- `solland_owned_contribution_in_joint_artifact`: a Solland-created contribution inside a jointly authored artifact
- `third_party_or_imported_unresolved`: imported material whose origin or license must be resolved
- `unresolved`: ownership or origin requires documentary or legal review

## Controlling documentary evidence

### MECHA paper v1.2

Zenodo DOI: `10.5281/zenodo.20668225`

The deposited paper states:

- Charles R. Rupp developed the MECHA tuple semantics, HSRS framework, Empty Cockpit doctrine, governance invariants and manuscript draft.
- Njål Gaute Solland developed the TLA+ specification, conducted model checking, validated safety properties, provided production implementation context and integrated verification results.
- Each author retains copyright in their respective contributions.
- The integrated paper is jointly attributed and released under CC BY 4.0.

Resulting classification:

- paper: `historical_joint_work`
- MECHA/EFA semantics: Rupp contribution
- TLA+ model, model checking, verification results and VALO infrastructure descriptions: `solland_owned_contribution_in_joint_artifact`

## Owner clarifications recorded

On 2026-07-11 Njål Gaute Solland clarified that:

- GEA is his / VALO-owned work.
- Ambient Overlay is his / VALO-owned work.
- The MECHA formal model was created by him and is his contribution.

These clarifications are recorded in:

- `docs/ip/OWNERSHIP_CLARIFICATION_LOG_2026-07-11.md`
- `docs/ip/MECHA_FORMAL_MODEL_OWNERSHIP.md`
- `docs/ip/IP_CLASSIFICATION_MATRIX.md`

## Completed cleanup

### VAIG README

Classification: `active_dependency_removed`

Action:

- removed MECHA from the active runtime dependency chain
- replaced collaborator-specific authority framing with explicit human and organizational authority inputs
- replaced ACS/VACS with the clean-room RACS boundary
- preserved historical references outside the normative runtime map

### Authoritative SYSTEM_MAP.md

Classification: `active_dependency_removed`

Previous condition:

- listed MECHA as a native active architecture layer
- used ACS/VACS as the active standard path
- mixed historical collaboration constructs with current VALO components

Action:

- replaced the old map with the current VALO architecture
- defined Speider, BARO, VALO Harness, VAIG, REHT, RACS, VALO Core and Execution as the active path
- moved MECHA/EFA to the historical collaboration boundary
- recorded the exact Zenodo contribution split
- added claim-maturity and AI-echo rules

Reason:

The active implementation does not depend on MECHA or EFA. The old map created a false implication that temporary collaboration framing remained part of the current runtime architecture.

### VAIG INDEX.md

Classification: `active_dependency_removed`

Action:

- removed MECHA, ACS and VACS from the current architecture index
- linked the IP, provenance and ownership records
- marked older collaboration-stack documents as historical rather than normative

### Current GEA architecture

File: `docs/GEA_CURRENT_ARCHITECTURE_2026-07-11.md`  
Classification: `valo_owned_with_external_reference`

Action:

- created a clean active GEA definition
- removed collaboration-specific frameworks from the normative architecture
- preserved the older GEA research note as historical provenance

### Ambient Overlay

File: `valo-platform/packages/ambient-overlay/README.md`  
Classification: `valo_owned_with_external_reference`

Action:

- added explicit VALO ownership and provenance language
- confirmed no Charles Rupp, MECHA or EFA runtime dependency in the active README
- created a platform-local trace register

### MECHA formal model

Classification: `solland_owned_contribution_in_joint_artifact`

Action:

- separated publication authorship from formal-model ownership
- recorded the exact Zenodo DOI and author-contribution statement
- documented Solland ownership of the TLA+ specification, model checking, verification results and VALO implementation context

### AI-assisted authorship and echo risk

File: `docs/ip/AI_ASSISTED_AUTHORSHIP_AND_ECHO_RISK.md`

Action:

- established that AI repetition or multi-model agreement is not independent validation
- required separate attribution for concepts, prose, diagrams, formal models, code, tests and verification
- established claim-maturity labels

### IP classification matrix

File: `docs/ip/IP_CLASSIFICATION_MATRIX.md`

Action:

- classified current VALO components, historical joint works, Solland-owned contributions, Rupp contributions, third-party material and unresolved artifacts
- established evidence hierarchy and handling rules

## Remaining active-file review

### VAIG — priority 1

- `SUBMISSION_PACKAGE.md`
- `docs/eu_submission/index.md`
- `docs/eu_submission/00_submission_package.md`
- `docs/eu_submission/01_executive_summary.md`
- `docs/eu_submission/06_local_node_normative_anchor.md`
- `docs/architecture/vaig-execution-boundary.md`
- `docs/architecture/EXECUTION_BOUNDARY_ARCHITECTURE.md`

These files may be active-facing and must not present MECHA/EFA as required runtime dependencies. Joint submission artifacts must instead be clearly marked historical or jointly attributed.

### VAIG — priority 2 historical/research

- `docs/GEA_VALO_2_1_2026-07-01.md`
- `docs/GEA_GEAS_BINDING_GOVERNANCE_CONDITION_2026-07-01.md`
- `docs/VALO_2_2_EXECUTION_GOVERNANCE_CLOSED_LOOP_2026-07-01.md`
- `docs/VALO_MISSING_PAPERS_SKELETON_2026-07-01.md`
- `docs/research/`
- `docs/imported/`

These should normally receive status headers and provenance notes rather than destructive rewriting.

### VALO Core

- `scripts/run_tlc.sh`
- `mcp_server.py`
- `docs/architecture/PRE_INTENT_GOVERNANCE_ALIGNMENT.md`
- `validation.md`
- `whitepaper.md`
- `docs/analysis/`

Code comments and scripts must distinguish a model name or historical test fixture from an active framework dependency.

### VALO Platform

- `docs/governability-architecture-position.md`
- `docs/repository-map.md`
- `PHASE_19_20_SUMMARY.md`
- `docs/architecture/valo-configuration-manager.md`
- `docs/ARCHITECTURE_COMPLETE_SUMMARY.md`
- `docs/VALO_8BLIND_MEN_GOVERNANCE_ELEPHANT.md`
- source comments or enums using MECHA as a native VALO layer

## What is actually joint

Current evidence supports joint classification only where the artifact itself is explicitly co-authored or demonstrably developed together:

- the MECHA paper as an integrated publication
- the EFA-VALO EU discussion paper according to its deposited author record
- explicitly co-authored drafts
- meeting records and correspondence from the collaboration
- text or diagrams directly copied from jointly developed material

The formal TLA+ model is not included in this list. It is a Solland-owned contribution inside the joint MECHA publication.

## Preservation rule

- Joint publications remain intact with attribution.
- Individually owned contributions inside joint works preserve both the joint publication record and the contribution-specific ownership statement.
- Historical files receive provenance headers or archival classification.
- Active architecture must not silently inherit historical collaboration dependencies.
- Git history must not be rewritten.

## Active architecture rule

Charles Rupp, MECHA, EFA or other collaboration-specific constructs may appear in active documentation only when:

1. the dependency is real and implemented,
2. origin and permission are documented,
3. the dependency is intentionally retained.

Otherwise the reference is external, historical or removed from the active architecture and recorded here.

## Git preservation

Original states remain available in repository history and backup branches:

- `VAIG: backup/pre-charles-ip-cleanup-2026-07-11`
- `valo-platform: backup/pre-ip-cleanup-2026-07-11`
- `valo-v5-core: backup/ip-cleanup-2026-07-11`

No Git history was rewritten.
