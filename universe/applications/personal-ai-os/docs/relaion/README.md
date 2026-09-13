# relAIon

This is the canonical home for relAIon-specific architecture.

Ownership rule:

- PersonalAI-OS owns the individual: identity, seed, memory, development, self-model, relationships, capability use and continuity.
- valo-platform owns generic infrastructure: governance, REHT/RACS, gateways, evidence, generic context compilation and governed effect paths.

relAIon-specific concepts must live here or explicitly depend on this repository. Generic platform primitives must not be duplicated here.

Canonical developmental invariant:

`Alpha owns becoming. The system owns boundaries.`

Naming and lineage invariant:

- current canonical name: `relAIon`
- former name: `Relygon`
- Relygon is historical relAIon lineage, not a separate product or architecture
- all legacy Relygon material is governed by `docs/relaion/relygon-migration.md`
- historical source that must retain the former name lives under `docs/relaion/legacy/relygon/`

Architecture map:

- `src/paios/seed.py` — developmental seed
- `src/paios/memory.py` — personal memory semantics
- `src/paios/development.py` — experience, consolidation, forgetting, proficiency, learning targets, self-model and evidence-backed relational capability realization
- `src/paios/continuity.py` — persistence of identity across sessions and migration
- `src/paios/maturity.py` — maturity/autonomy progression
- `src/paios/peripherals.py` — external surfaces and embodiment
- `docs/relaion/development.md` — development contract
- `docs/relaion/capabilities.md` — borrowed/developed ability, provider model, relational realization and realization-vs-detection semantics
- `docs/relaion/architecture.md` — repository boundaries and dependency direction
- `docs/relaion/relygon-migration.md` — legacy Relygon absorption, provenance and estate ownership rules

Dependency direction:

`relAIon -> PersonalAI-OS domain model -> valo-platform governed infrastructure`

Never the reverse for identity or development semantics.
