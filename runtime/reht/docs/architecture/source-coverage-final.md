# Final source coverage — execution-governance audit

Status: COMPLETE
Date: 2026-08-23
Audit base: `5ecf09f2ef94c83a04b10a7ef4bcf3becc92a32d`

Completion rule: every code family in the audited portfolio that can own or modify operative authority/state, authorize or physically perform a consequence, narrow/interrupt a live consequence path, issue execution credentials, validate execution continuity, admit execution evidence, verify poststate, or compile a consequence-bearing workflow has been assigned a semantic role and preservation status. Pure domain/research/formatting utilities are classified by their owning family rather than treated as independent runtime layers.

This file supersedes `source-coverage-index.md` where that file still says PENDING.

## Fully covered authority/state owners

### `nsolland/valo-kernel`
Covered execution-governance families:
- deterministic event/state engine and reducers
- event-chain integrity and replay
- execution context and signed context origin
- governed workspace compilation/conformance/execution binding
- semantic workspace
- attested/confidential workspace
- evidence/state admission
- persistent state admission/binding
- authority projection v1/v2
- execution-authority assurance/revocation epochs/checkpoints/leases
- emergency governance
- actor standing
- consequence governance
- state-resolution / causal continuity
- dependency-risk assessment
- LLMOps substrate binding
- agent-risk assurance
- BARO postcondition hook
- uniform/governed-whisker contracts and builders

Classification: canonical operative state owner; no external-effect execution path.

### `nsolland/valo-reht`
Covered:
- `reht.py`
- `contracts.py`
- execution requirements and all subordinate checks
- approver-authority gate
- confidential-execution continuity
- outcome feedback
- security assurance / release evidence gate
- `effect_boundary.py`
- tests/contracts supporting the above

Classification: sole intended execution-authorization owner. Current `EffectBoundary` is only a partial mechanical consequence substrate.

## Fully covered consequence-path mechanics

### `nsolland/valo-gateway`
Covered:
- `gateway/core.py`
- runtime control plane
- boundary replay contracts
- tool adapters / physical non-bypass
- resource budget ledger
- governed message security
- execution receipts

Classification: non-authoritative but carried required interlocks and consequence-path invariants.

### `nsolland/valo-platform` containment
Covered:
- containment gate
- containment models
- containment controller
- containment receipt/binding chain
- egress/path validation

Classification: non-authoritative containment/interrupt layer; currently orphaned from simplified REHT effect path.

### `nsolland/valo-platform/execution_substrate`
Covered top-level semantic modules:
- `models.py`
- `protocol.py`
- `policy_compiler.py`
- `in_memory.py`
- `authorization_proof.py`
- `runtime_capabilities.py`
- `governed_runtime_capabilities.py`
- `capability_credentials.py`
- `credentials.py`
- `evidence.py`
- `aaec_trajectory.py`
- `hap_authority_bridge.py`
- `hap_authority_trust.py`
- `errors.py` and package export surfaces classified as supporting mechanics

Covered adapters:
- `adapters/capability_bound.py`
- `adapters/cubesandbox.py`
- `adapters/qm_sandbox.py`

Covered credential-delivery subsystem:
- `credential_delivery/models.py`
- `pdp.py`
- `cdp.py`
- `leases.py`
- `proof_of_possession.py`
- `revocation.py`
- `workload_identity.py`
- `audit.py`
- `composition.py`
- `signing.py`
- `providers/base.py`
- `providers/proxy.py`
- export/helper modules classified with their parent subsystem

Classification: already contains the richer provider-neutral mechanical execution substrate the simplified REHT `EffectBoundary` was trying to recreate: prepare, precommit revalidation, exact authorization proof, replay protection, default-deny egress, payload binding, workload identity, one-shot capability credentials, bounded/non-renewable leases, proof of possession, revocation, audit/evidence, deterministic teardown, provider adapters and post-effect receipts. It does not own legitimacy/authority.

## Fully covered execution artifact / continuity layers

### `nsolland/Racs`
Covered:
- canonical evaluation/determination/clearance boundary chain
- cross-artifact digest continuity
- boundary binding validation
- normative/non-execution receipt semantics
- active/embodied session continuity
- sensor/watcher runtime signals
- PAUSE/STOP/REAUTHORIZE/ROLLBACK/HANDOVER/HALT semantics
- bound modification and fail-closed recovery

Classification: representation/integrity/continuity; must not become a second authorization owner.

### `nsolland/Veritas`
Covered:
- gateway execution observation verification
- observation package conversion
- service admission/tamper rejection
- WORM append-only/hash-chain integrity

Classification: verified evidence admission and immutable execution evidence; not authority.

## Fully covered compile/orchestration safety

### `nsolland/valo-workflow-isa`
Covered consequence-relevant compiler/runtime families:
- WRITE authority requirements
- probabilistic-output-to-WRITE prohibition
- irreversible/idempotency constraints
- uncertain-effect retry/reconcile
- HALT/COMPENSATE semantics
- Gateway -> Veritas -> Kernel -> BARO completion path

Classification: compile/runtime orchestration invariants, not authority ownership.

### `nsolland/valo-function-fabric`
Covered:
- composition validation
- risk/autonomy monotonicity
- child effect visibility
- authority/evidence/rights/purpose preservation

Classification: compile-time governance monotonicity.

## Fully covered external evidence/trust boundary

### `nsolland/action-attestation-service`
Covered:
- attestation models and adapters
- signature/trust/revocation validation
- external gate evidence normalization
- explicit no-authority-creation contracts

Classification: external evidence/trust adapter; not clearance.

## Fully covered VAIG execution-governance surfaces

Current bounded/subordinate paths covered:
- `vaig/evaluation_report.py`
- `vaig/normative_governance.py`
- `vaig/security_pipeline.py`
- `vaig/aaec_trajectory.py`
- `vaig/guard.py`
- `vaig/why_gate.py`
- `vaig/continuity_assessment.py`
- `vaig/continuity_wire.py`
- `vaig/transition_risk.py`
- `vaig/orchestrator.py`
- `vaig/judge/multiverse.py`
- `vacs/src/policy_engine.py`
- `vacs/src/clearance.py`
- `vacs/src/execution_adapter.py`

Legacy/conflicting paths covered:
- `vaig/aarm.py`
- `vaig/api.py`
- `src/authority_gate.py`

Legacy local optimization/support root covered in full:
- `src/roi_gate.py`
- `src/spend_gate.py`
- `src/model_router.py`
- `src/efficiency_engine.py`
- `src/value_weighting.py`
- `src/reward_economy.py`

Classification: newer VAIG/VACS path correctly says evaluation-only + REHT clearance. AARM/API/AuthorityGate remain conflicting legacy execution-authority surfaces. Local ROI/spend/router ALLOW vocabularies are semantic collisions but not execution authority when kept subordinate.

## Fully covered BARO execution-governance surfaces

Covered:
- `src/valo_baro/core/reality_package.py`
- `src/valo_baro/attention_whiskers.py`
- `src/valo_baro/evidence_loop.py`
- `src/valo_baro/incident_poststate.py`
- `src/valo_baro/baro_observability_convergence.py`
- `src/valo_baro/api.py`
- `src/valo_baro/falsification.py`
- convergence/lens families classified as RealityPackage-producing observation families

Repository searches for execution-authority/authorize/HALT/ALLOW surfaces were reviewed. No BARO source path was found that owns execution authorization. The canonical RealityPackage actively rejects authority/decision/admission/clearance/permit semantics in observation keys.

Classification: observation/evidence only. The missing property is mandatory post-effect wiring, not BARO authority separation.

## Closure

No execution-governance-relevant family in the audit scope remains `UNKNOWN`.

The remaining `MISSING`, `PARTIAL` and `PRESERVED_ORPHANED` labels are architecture findings, not unreviewed source coverage. They identify semantics whose code exists in the portfolio but is not on the current canonical consequence path, or whose replacement has not been proven equivalent.
