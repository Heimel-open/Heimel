# Source coverage index

Date: 2026-08-23
Branch: `audit/full-semantic-architecture-map`

This file records what source has actually been read in the semantic audit. `COVERED` means executable symbols/contracts were inspected and assigned a role in the function map or a repo-specific symbol map. `PARTIAL` means only part of the file/module has been read. `PENDING` means it remains in scope and no semantic conclusion may be drawn from its absence here.

## valo-kernel

COVERED:
- `src/valo_kernel/kernel/engine.py`
- `src/valo_kernel/kernel/integrity.py`
- `src/valo_kernel/kernel/queries.py`
- `src/valo_kernel/kernel/reducers.py`
- `src/valo_kernel/kernel/execution_context.py`
- `src/valo_kernel/kernel/context_origin.py`
- `src/valo_kernel/kernel/workspace.py`
- `src/valo_kernel/kernel/attested_workspace.py`
- `src/valo_kernel/kernel/persistent_state.py`
- `src/valo_kernel/kernel/uniform.py`
- `src/valo_kernel/kernel/semantic_disclosure.py`
- `src/valo_kernel/kernel/baro.py`
- `src/valo_kernel/contracts/uniform_whisker.py`
- `src/valo_kernel/contracts/persistent_state.py`
- `src/valo_kernel/contracts/actor_standing.py`
- `src/valo_kernel/contracts/verification_proof.py`
- `src/valo_kernel/actor_standing.py`
- `src/valo_kernel/authority_projection.py`
- `src/valo_kernel/authority_projection_v2.py`
- `src/valo_kernel/execution_authority_assurance.py` (major artifact families inspected)
- `src/valo_kernel/consequence_governance.py`
- `src/valo_kernel/state_resolution.py`
- `src/valo_kernel/semantic_disclosure.py`
- `src/valo_kernel/semantic_workspace.py`
- `src/valo_kernel/dependency_risk.py`
- `src/valo_kernel/llmops_substrate.py`
- `src/valo_kernel/agent_risk_attestation.py`
- `src/valo_kernel/confidential_workspace.py`

Key finding: Kernel is not a flat state store. It contains independent semantic families for state admission, workspace projection/conformance, semantic provenance, confidential substrate binding, authority projection/revocation assurance, emergency governance, actor standing, state-resolution continuity, persistent state, verification proof, BARO postconditions and orphaned uniform-whisker control.

## valo-reht

COVERED:
- `src/valo_reht/contracts.py`
- `src/valo_reht/reht.py`
- `src/valo_reht/effect_boundary.py`
- `src/valo_reht/execution_requirements.py`
- `src/valo_reht/approver_authority.py`
- `src/valo_reht/confidential_execution.py`
- `src/valo_reht/governed_workspace.py`
- `src/valo_reht/outcome_feedback.py`
- `src/valo_reht/evidence_gate.py`
- `src/valo_reht/security_assurance.py`
- `src/valo_reht/owasp_llm_2026.py`
- `src/valo_reht/release_manifest.py`

Key finding: REHT already carries many fail-closed invariant checks, but `EffectBoundary` is only a subset of the former mechanical consequence path and does not make post-effect evidence/admission mandatory.

## valo-gateway

COVERED:
- `src/valo_gateway/gateway/core.py`
- `src/valo_gateway/gateway/control.py`
- `src/valo_gateway/contracts/boundary.py`
- `src/valo_gateway/contracts/models.py`
- `src/valo_gateway/tool_adapters/base.py`
- `src/valo_gateway/resource_budget.py`
- `src/valo_gateway/message_security.py`

Key finding: Gateway carried non-authoritative but required mechanics: physical non-bypass, runtime halt/revocation, commit-time revalidation, structural replay, resource consumption and exact execution receipts.

## valo-platform containment

COVERED:
- `src/valo_platform/containment/gate.py`
- `src/valo_platform/containment/models.py`
- `src/valo_platform/containment/controller.py`
- `src/valo_platform/containment/receipts.py`
- `src/valo_platform/governance/containment_attestation.py`

Key finding: deny-by-default direct egress, exact runtime/environment/credential/path bindings, global halt, permit/credential invalidation, restart block and human recommissioning are separate safety semantics and are not wired into current `EffectBoundary`.

## valo-platform execution_substrate

COVERED:
- `src/valo_platform/execution_substrate/models.py`
- `src/valo_platform/execution_substrate/protocol.py`
- `src/valo_platform/execution_substrate/policy_compiler.py`
- `src/valo_platform/execution_substrate/in_memory.py`
- `src/valo_platform/execution_substrate/authorization_proof.py`
- `src/valo_platform/execution_substrate/runtime_capabilities.py` (major service/lifecycle symbols inspected)
- `src/valo_platform/execution_substrate/capability_credentials.py`
- `src/valo_platform/execution_substrate/credentials.py`
- `src/valo_platform/execution_substrate/evidence.py`
- `src/valo_platform/execution_substrate/adapters/capability_bound.py`
- `src/valo_platform/execution_substrate/adapters/cubesandbox.py`
- `src/valo_platform/execution_substrate/adapters/qm_sandbox.py`
- `src/valo_platform/execution_substrate/credential_delivery/models.py`
- `src/valo_platform/execution_substrate/credential_delivery/pdp.py`
- `src/valo_platform/execution_substrate/credential_delivery/cdp.py`
- `src/valo_platform/execution_substrate/credential_delivery/leases.py`
- `src/valo_platform/execution_substrate/credential_delivery/proof_of_possession.py`
- `src/valo_platform/execution_substrate/credential_delivery/revocation.py`
- `src/valo_platform/execution_substrate/credential_delivery/workload_identity.py`
- `src/valo_platform/execution_substrate/credential_delivery/audit.py`
- `src/valo_platform/execution_substrate/credential_delivery/composition.py`
- `src/valo_platform/execution_substrate/credential_delivery/providers/base.py`
- `src/valo_platform/execution_substrate/credential_delivery/providers/proxy.py`

PENDING / still in scope:
- `src/valo_platform/execution_substrate/aaec_trajectory.py`
- `src/valo_platform/execution_substrate/governed_runtime_capabilities.py`
- `src/valo_platform/execution_substrate/hap_authority_bridge.py`
- `src/valo_platform/execution_substrate/hap_authority_trust.py`
- remaining credential-delivery signing/provider plumbing and any adapter-specific helpers not yet assigned.

Key finding: this package already implements a provider-neutral mechanical execution boundary with default-deny egress, exact precommit binding, durable authorization replay, short-lived capability-bound credentials, workload identity, PoP, audit fail-closed, normalized evidence, revocation and deterministic teardown. PR #38 duplicated only a smaller subset in `valo-reht`.

## Racs

COVERED:
- `reference/bindings/v0.2/python/src/racs_v02/models.py`
- `.../validation.py`
- `.../verification.py`
- `.../boundary_crossing.py`
- `.../boundary_validation.py`
- `.../continuity.py`
- `.../continuity_verification.py`
- `.../continuity_validation.py`
- `.../normative_receipt.py`

Key finding: RACS is not merely a decision enum. It carries cross-artifact binding integrity, response floors and active-session continuity/intervention semantics. These can be non-authoritative and still required.

## valo-workflow-isa

COVERED:
- `src/valo_workflow_isa/ports/boundaries.py`
- `src/valo_workflow_isa/compiler/compiler.py`
- `src/valo_workflow_isa/graph/invariants.py`
- `src/valo_workflow_isa/effects/system.py`
- `src/valo_workflow_isa/runtime/engine.py`
- `src/valo_workflow_isa/stdlib/handlers.py`
- `src/valo_workflow_isa/patterns/incident.py`

Key finding: compile-time effect governance, uncertain-effect retry/reconcile, HALT/COMPENSATE and verified poststate are orchestration invariants, not REHT authority semantics.

## valo-function-fabric

COVERED:
- `src/valo_function_fabric/compiler/governance.py`
- `src/valo_function_fabric/compiler/effects.py`
- `src/valo_function_fabric/contracts/function.py`

Key finding: composition must be governance-monotone; risk/autonomy/effects/authority/evidence/rights/purpose cannot silently weaken.

## Veritas

COVERED:
- `src/veritas/execution.py`
- `src/veritas/receipts.py`
- `src/veritas/worm.py`
- `src/veritas/service.py`

Key finding: Veritas does not authorize, but it enforces verified execution handoff and append-only/tamper-evident evidence admission.

## Baro

COVERED:
- `src/valo_baro/incident_poststate.py`

PARTIAL:
- broader BARO lenses/observation modules remain to be classified.

Key finding so far: postcondition/reality divergence is independent from execution authorization and is not mandatory on current `EffectBoundary` path.

## VAIG

COVERED:
- `vaig/guard.py`
- `vaig/why_gate.py`
- `vaig/continuity_assessment.py`
- `vaig/continuity_wire.py`
- `vaig/transition_risk.py`
- `vaig/aarm.py` (authoritative-verdict model inspected)
- `vaig/agent_loop/gate.py`
- `vaig/agent_loop/loop.py`
- `vaig/orchestrator.py`

PENDING:
- legacy authority/gate modules and remaining code paths that may still treat VAIG/AARM as execution authority.

Key finding: AARM explicitly calls its verdict model authoritative while the current architecture assigns sole execution authorization to REHT. This is an unresolved legacy authority conflict, not a cosmetic naming issue.

## action-attestation-service

COVERED:
- `src/aas/core.py`
- `src/aas/authority_adapter.py`
- `src/aas/gate_adapter.py`
- `src/aas/reht_gate_context.py`
- `src/aas/authority_state.py`
- `src/aas/ledger.py`

Key finding: AAS is a trust-boundary/evidence normalizer. It explicitly forbids authority/permit/clearance creation and can therefore remain subordinate without being optional where its evidence is relied upon.

## Audit rule

No `PENDING` area may be used as evidence that a component is redundant. No `MISSING`/`PARTIAL`/`PRESERVED_ORPHANED` blocking invariant may be deleted or ignored. Coverage is source-backed, not inferred from architecture diagrams.
