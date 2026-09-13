# Charles Rupp / MECHA Trace Register

Date: 2026-07-11
Repository: `nsolland/valo-v5-core`

## Current active boundary

The active Core architecture is:

- VAIG evaluates runtime governance conditions
- REHT defines admissibility semantics
- VALO Core enforces bounded execution-state transitions
- human and organizational authority are external governed inputs
- RACS defines action and receipt contracts

MECHA, EFA, HSRS and Empty Cockpit are not active runtime dependencies.

## Formal model ownership clarification

The deposited MECHA paper is a jointly authored publication by Charles R. Rupp and Njål Gaute Solland.

The publication record separates contributions:

- Charles R. Rupp: EFA semantics, MECHA tuple, HSRS, Empty Cockpit and related definitions.
- Njål Gaute Solland: TLA+ specification, model-checking implementation, verification results and VALO infrastructure descriptions.

For this repository:

- the MECHA paper remains a joint historical publication
- the TLA+ specification and model-checking contribution are classified separately as Solland-created work
- VALO Core implementation and verification assets are VALO/Solland-owned unless a specific file contains separately documented third-party material

Joint publication authorship must not be interpreted as joint ownership of the Rust implementation, active Core state machine, independent verification assets or unrelated VALO architecture.

## Completed actions

### Active README

Collaboration-specific framework references were removed from the active architecture description.

### Default formal-verification entry point

`scripts/run_tlc.sh` now defaults to:

`formal-verification/ValoStateMachine.tla`

Historical models must be selected explicitly.

### Historical model directory

`mecha/README.md` now classifies the directory as historical research and joint-publication support material. It is not the active Core model directory.

### Pre-intent architecture

`docs/architecture/PRE_INTENT_GOVERNANCE_ALIGNMENT.md` now uses current VAIG, REHT, Core and RACS boundaries and no longer presents MECHA or BOA as active architecture dependencies.

## Preserved evidence

Original wording remains available in Git history and in:

`backup/ip-cleanup-2026-07-11`

No history was rewritten. Historical and jointly authored material remains preserved.

## Remaining review

Priority review remains for:

- `mcp_server.py`
- `validation.md`
- `whitepaper.md`
- `readme.md`
- `docs/analysis/analysis_v5_2026-06-13.md`
- `docs/analysis/valo_research_group_complete_analysis.md`
- historical files under `mecha/`

Specific `mcp_server.py` issues already identified:

- legacy `ACS distrust levels` wording
- an `ACS §9.1` reference with unresolved origin
- ambiguous use of `ACS` near OWASP Agentic Security Initiative content
- coverage claims that require technical verification and current primary-source validation

These references must be corrected without changing runtime behavior until the code path and test impact are reviewed.

## Rule

Historical references may remain with accurate attribution. They must not be indexed, imported or described as normative active Core architecture.
