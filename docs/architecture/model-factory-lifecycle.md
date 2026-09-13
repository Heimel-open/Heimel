# Governed model-factory lifecycle

## Canonical path

The model factory is not the render broker and Unsloth is not a governance authority.

The complete lifecycle is:

governed source/corpus
→ dataset/state admission + provenance
→ governed workspace
→ Unsloth-led training/optimization handoff
→ fresh VAIG / reht / RACS / PEP execution chain
→ execution receipt
→ candidate model receipt
→ Honest Evaluation
→ MAL admissibility
→ admitted model registry
→ render-broker or local inference placement
→ runtime VAIG → reht → RACS → governed effect path → Veritas.

`lib/unsloth_factory.py` owns the pre-execution factory handoff. `lib/model_lifecycle.py` starts after that handoff and owns deterministic lifecycle validation from the resulting artifact to registry eligibility.

## Ownership boundaries

VALO owns:
- governed source and dataset admission
- purpose, mandate, workspace and authority references
- provenance continuity
- pre-execution governance bindings
- candidate receipt semantics
- Honest Evaluation evidence binding
- MAL admission state
- admitted model registry state
- runtime governance.

Unsloth owns:
- training, fine-tuning and optimization mechanics
- supported quantization and packaging mechanics
- engine-specific implementation details.

Render broker owns:
- compute/provider placement
- runtime placement of already-admitted model artifacts
- no policy or admission authority.

## Invariants

GOVERNED_DATASET_ONLY
Only already-admitted state/data with provenance may enter the governed model-factory handoff.

UNSLOTH_NO_AUTHORITY
Engine success, model quality, loss curves, self-reported confidence or possession of compute credentials cannot create authority or admissibility.

NULL_EFFECT_ON_DENY
A non-ALLOW governed execution chain cannot produce a valid candidate receipt.

CANDIDATE_NOT_ADMITTED
Training success creates `CANDIDATE`, never `ADMITTED`. A candidate cannot be handed to runtime placement.

PROVENANCE_CONTINUITY
The candidate and admitted model records preserve workspace, state, dataset, provenance, engine runtime, PEP handoff and execution-receipt lineage.

EVALUATION_BOUND
Honest Evaluation must bind to the exact candidate receipt digest. Unbound or failed evaluation cannot admit a model.

MAL_BOUND
MAL must bind to the exact candidate receipt digest and explicitly return `ADMIT`. `REJECT` and `DEFER` remain non-admitted.

BROKER_NOT_POLICY
Placement cannot manufacture model admissibility. The render broker consumes an admitted record; it does not create one.

NO_AUTO_PROMOTION
Neither Unsloth, the Factory OS, evaluation infrastructure nor the broker may automatically promote training output to admitted runtime state.

LICENSE_BOUNDARY
VALO integration remains on separately reviewed/pinned Unsloth engine surfaces. Studio/UI copyleft surfaces are not made a required core dependency by this lifecycle contract.

## Machine-readable records

`schemas/model_candidate_receipt.schema.json`
defines the post-execution candidate artifact record.

`schemas/model_admission_record.schema.json`
defines the registry-eligible admitted model record.

The implementation is intentionally provider-neutral after candidate creation. The candidate records the engine identity and runtime digest, but admission semantics do not depend on Unsloth being able to grant or infer authority.
