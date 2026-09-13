# Headless workflow harness claim

Status: IMPLEMENTED — awaiting CI/QC
Owner: execution worker
Repository: `nsolland/valo-factory`
Canonical base SHA: `b2c650ec5fecda31736365595217f8f45275e6f9`
Branch: `feat/headless-workflow-harness`
Draft PR: `#61`

## Active delivery

Adopt the Ori-style harness pattern into VALO Factory as provider-neutral, headless orchestration: canonical workflow primitives callable from any surface, with model/provider selection outside the workflow contract.

## Owned files

- `work/HEADLESS_WORKFLOW_HARNESS_CLAIM.md`
- `lib/workflow_harness.py`
- `schemas/workflow-primitive.schema.json`
- `tests/test_workflow_harness.py`
- `docs/architecture/headless-workflow-harness.md`

## Dependencies

- `lib/long_horizon.py`
- `lib/provider_entitlements.py`
- Factory orchestrator worker selection
- VAIG evaluation
- REHT authorization
- RACS decision expression
- Veritas execution/evidence receipts

## Boundary

Workflow definitions, harness state, provider selection, context and memory are orchestration inputs only. They never grant authority. Any consequence-bearing action remains subject to VAIG -> REHT -> RACS before execution and Veritas evidence after execution.

## Evidence

- Isolated contract test: `9/9` passed before push.
- GitHub PR CI/QC: pending on current head.
