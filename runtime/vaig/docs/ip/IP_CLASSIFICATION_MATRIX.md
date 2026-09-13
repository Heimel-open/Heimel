# VALO IP Classification Matrix

Date: 2026-07-11  
Status: active internal provenance control

This matrix separates component ownership, publication authorship, external references and unresolved material. It is an internal engineering record, not legal advice.

| Asset | Classification | Current owner / attribution | Treatment |
|---|---|---|---|
| VALO Platform | `valo_owned` | Njål Gaute Solland / VALO | active architecture |
| VAIG | `valo_owned` | Njål Gaute Solland / VALO | active runtime-governance component |
| REHT | `valo_owned_clean_room` | Njål Gaute Solland / VALO | active admissibility semantics; clean-room provenance required |
| RACS | `valo_owned_clean_room` | Njål Gaute Solland / VALO | active protocol work; no copying from archived ACS |
| VALO Core | `solland_valo_owned` | Njål Gaute Solland / VALO | deterministic state machine, implementation and verification assets |
| GEA | `valo_owned` | Njål Gaute Solland / VALO | active architecture; collaborator references are external or historical only |
| Ambient Overlay | `valo_owned` | Njål Gaute Solland / VALO | active product and capture architecture |
| BARO | `valo_owned` | Njål Gaute Solland / VALO | observation and intelligence layer |
| Speider | `valo_owned` | Njål Gaute Solland / VALO | collection, connectors and source provenance |
| VALO Harness | `valo_owned_emerging` | Njål Gaute Solland / VALO | orchestration layer; external papers are research inputs, not origin claims |
| Receipts / WORM implementation | `valo_owned_or_generic_pattern` | implementation owned by VALO; generic cryptographic patterns remain generic | document implementation-specific originality only |
| Continuous Integrity | `valo_owned_expression_with_generic_foundations` | current VALO formulation and implementation | do not claim ownership of generic continuous-monitoring concepts |
| State Admissibility | `valo_owned_expression_with_generic_foundations` | current VALO formulation and implementation | distinguish original architecture from generic admissibility terminology |
| MECHA paper v1.2 | `historical_joint_publication` | Charles R. Rupp and Njål Gaute Solland | retain dual attribution; CC BY 4.0 publication terms |
| MECHA tuple / EFA semantics / HSRS / Empty Cockpit | `rupp_contribution` | Charles R. Rupp | external or historical reference unless separately licensed/integrated |
| MECHA TLA+ formal model | `solland_owned_contribution_in_joint_artifact` | Njål Gaute Solland | may be used in VALO with contribution boundary preserved |
| MECHA model checking and verification results | `solland_owned_contribution_in_joint_artifact` | Njål Gaute Solland | preserve evidence and exact claim scope |
| EFA-VALO EU discussion paper | `historical_joint_publication` | named authors in deposited publication | retain attribution; not normative active architecture |
| Governability Engineering joint drafts | `historical_joint_or_mixed` | classify per version and author-contribution record | do not place in active architecture until provenance is resolved |
| Charles/Rupp meeting notes and correspondence | `historical_collaboration_record` | participants retain their respective material and rights | preserve, restrict and exclude from active architecture indexes |
| Archived ACS repository | `third_party_or_imported_unresolved` | based on external Agent Control Standard material | archive; do not use as RACS source |
| External papers, standards and market products | `external_reference` | respective authors/owners | cite; do not imply ownership or independent validation |
| AI-generated drafts | `ai_assisted_artifact` | human contribution owner subject to source rights | never treat as independent evidence; record human decisions and sources |

## Rules

1. Joint publication does not imply joint ownership of every underlying contribution.
2. Reference to a framework does not create dependency or ownership.
3. Generic ideas, mathematical methods, standards and common engineering patterns are not claimed as exclusive property.
4. Source text, diagrams, schemas and code must be traced individually.
5. AI assistance must be disclosed internally where it materially affected wording, structure or code generation.
6. New active architecture documents must use the current system map and RACS terminology.
7. Historical files must remain intact unless corrected through an explicit errata or provenance note.
8. Unresolved material must not be used as the foundation for public ownership claims.

## Evidence hierarchy

From strongest to weakest:

1. signed agreement or assignment
2. deposited publication with contribution and copyright statement
3. Git commit history and original source files
4. dated design records and correspondence
5. meeting notes confirmed by participants
6. owner clarification recorded after the fact
7. AI-generated summaries or reconstructions

AI-generated summaries are navigation aids only. They are not controlling ownership evidence.
