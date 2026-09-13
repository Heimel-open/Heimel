# Unsloth model lifecycle claim

Status: active
Owner: execution worker
Repository: nsolland/valo-factory
Canonical base SHA: de61886f6cea6c38e3d2045c93bce13e344f0f29
Branch: feat/unsloth-model-lifecycle
Draft PR: #99

Owned files:
- work/UNSLOTH_MODEL_LIFECYCLE_CLAIM.md
- lib/model_lifecycle.py
- schemas/model_candidate_receipt.schema.json
- schemas/model_admission_record.schema.json
- tests/test_model_lifecycle.py
- docs/architecture/model-factory-lifecycle.md

Dependencies:
- existing lib/unsloth_factory.py pre-execution governed PEP handoff
- Honest Evaluation evidence producer
- MAL admissibility decision producer
- admitted model registry consumer
- render-broker/local inference placement consumer
- existing VAIG -> reht -> RACS -> PEP -> Veritas execution path

Parallel ownership:
- PR #98 owns existing Unsloth adapter/tests and behavior-promotion/ReOPD files.
- This delivery does not modify those files.

Scope:
Close the post-training lifecycle gap. A successful Unsloth execution creates only a provenance-bound CANDIDATE receipt. Runtime eligibility requires independent Honest Evaluation and an explicit MAL ADMIT decision bound to the exact candidate receipt. Preserve dataset/state/workspace/engine/execution lineage into the admitted model record. No training execution, no automatic promotion, no authority transfer and no render-broker policy ownership.
