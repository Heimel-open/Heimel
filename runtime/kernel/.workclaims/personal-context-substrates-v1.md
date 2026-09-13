# Work claim: Personal Context Substrates v1

Owner: ChatGPT on behalf of Njål / VALO
Canonical base: a58ed4bab15ff9383911c0bc6d0425c6362cd532
Branch: feat/personal-context-substrates-v1

Active delivery: define the provider-neutral boundary for explicit personal knowledge stores and inferred personal-model substrates, using Obsidian and Honcho as non-canonical examples, while preserving Kernel ownership of governed/authoritative state and REHT ownership of consequence-bearing authorization.

Owned files:
- docs/personal_context_substrates_v1.md
- README.md
- .workclaims/personal-context-substrates-v1.md

Dependencies:
- docs/principal_authority_projection.md
- docs/organization_projection_boundary.md
- docs/governed_workspace_v1.md
- docs/state_admission_v1.md

Invariants:
- explicit personal knowledge is evidence/context, not authority merely because the principal stored it
- inferred personal models are non-authoritative and may never mint identity, mandate, delegation, rights or permission
- Obsidian, Honcho and equivalent providers are hot-swappable substrates, never Kernel dependencies
- inferred state must remain labelled as inference unless admitted through canonical state-admission rules
- no personal-model substrate may mutate WorldState directly
- consequence-bearing actions require fresh authoritative state and downstream REHT authorization
- provider confidence, memory persistence or behavioural prediction cannot widen authority
