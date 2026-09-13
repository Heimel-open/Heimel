# Full semantic function map — execution governance

Status: AUDIT IN PROGRESS
Date: 2026-08-23
Canonical audit base: `5ecf09f2ef94c83a04b10a7ef4bcf3becc92a32d`

This map reconstructs the execution-governance architecture from code, not component names. A component may be non-authoritative and still carry a required safety invariant. `Kernel + REHT` refers only to authority/state ownership; it does not by itself prove semantic preservation of every interlock, continuity mechanism, evidence path or compile-time restriction.

Status vocabulary:
- `PRESERVED_WIRED`: implementation exists and is demonstrably on the active production path.
- `PRESERVED_ORPHANED`: implementation exists but no active production wiring was found.
- `REPLACED_EQUIVALENT`: replacement is proven to preserve the same invariant.
- `PARTIAL`: some semantics survive but the original invariant is not fully covered.
- `MISSING`: required semantic behavior has no demonstrated destination on the current two-core effect path.
- `NON_AUTHORITATIVE_REQUIRED`: does not own authority/state but carries a required invariant.
- `OUT_OF_RUNTIME`: useful assurance/compile-time/research behavior, not required on every commit path.
- `UNKNOWN`: not yet classified.

## 1. Authoritative ownership

### valo-kernel

`kernel/execution_context.py::build_execution_context`
- Purpose: produce the fresh, complete execution context consumed by REHT.
- Invariants: verified executable identity; active authority/delegation projection; current purpose/rights/obligations/contracts/constraints/evidence; exact target state; state root; event position; nonce; optional governed-workspace binding; fail closed on identity ambiguity, stale/changed workspace dependencies or action/purpose mismatch.
- Authority effect: none. Kernel exposes state; it does not authorize.
- Current status: `PRESERVED_WIRED` through `RealReht` context construction where callers use Kernel directly.

`kernel/admission.py::{evaluate_state_admission,create_admission_event}` and seal helpers
- Purpose: prevent arbitrary/provider-produced material from becoming operational Kernel state.
- Invariants: admitted evidence identity/integrity, tenant binding, trusted-provider policy, freshness, contradictions/unresolved references, no provider authority creation.
- Authority effect: none.
- Current status: `NON_AUTHORITATIVE_REQUIRED`; state-integrity path independent of REHT.

`contracts/persistent_state.py::PersistentStateBinding`
`kernel/persistent_state.py::{persistent_content_digest,seal_persistent_state_binding,verify_persistent_state_binding}`
- Purpose: govern durable memory/config/instruction/handoff/artifact material.
- Invariants: source must be admitted evidence; exact workspace/state-root/source/purpose/content bindings; fresh admission required; no self-propagation; no authority/clearance creation.
- Current status: `NON_AUTHORITATIVE_REQUIRED`; not replaced by two-core effect boundary.

`authority_projection.py::{AuthorityStateReference,ExecutionEndpoint,PrincipalAuthoritySemantics,ExecutionAuthorityProjection,seal_principal_authority_semantics,project_authority_to_endpoints}`
- Purpose: preserve one canonical principal-authority meaning across multiple execution rails.
- Invariants: action/capability/target/purpose/delegation/fresh-state consistency; projections cannot widen authority or outlive dependencies; endpoint description cannot create authority.
- Current status: `NON_AUTHORITATIVE_REQUIRED`; rail projection semantics remain separate from REHT.

`authority_projection_v2.py::{PrincipalAuthoritySemanticsV2,ExecutionAuthorityProjectionV2,seal_principal_authority_semantics_v2,project_authority_to_endpoints_v2}`
- Adds actor-decision standing, authority origination, represented-principal separation, delegation-depth constraints and stricter lifetime binding.
- Current status: `NON_AUTHORITATIVE_REQUIRED`.

`execution_authority_assurance.py` family
- `Ed25519ExecutionArtifactSigner`, signing helpers: signed execution-assurance artifacts.
- `AuthorityLeaseBasis` / `seal_authority_lease_basis`: authority+delegation+purpose+fresh authority state may only attenuate.
- `RevocationNotice` / `issue_revocation_notice` / `verify_revocation_notice`: monotonic signed revocation epoch transition.
- `RevocationEpochState` / seal/verify: signed current revocation state.
- `RevocationAcknowledgement` / issue/verify: execution-node acknowledgement of exact epoch state.
- `RevocationCheckpoint` / `assess_revocation_checkpoint`: fail closed on stale/unknown revocation propagation.
- `ExecutionAuthorityLease` family: short-lived attenuated execution lease; explicitly no clearance/no external effect.
- Current status: `NON_AUTHORITATIVE_REQUIRED`; distributed authority/revocation assurance, not replaced by a process-local authorization call.

### valo-reht

`contracts.py::{DecisionResult,RehtPort}`
- Current decision plane: exactly `ALLOW | STEP_UP | DENY` with construction-time rejection of other values.
- Status: `PRESERVED_WIRED`.

`reht.py::RealReht.authorize`
- Purpose: sole runtime authorization decision for one exact consequential transition now.
- Invariants: current identity, authority, scope, purpose, constraints, freshness; optional governed-workspace continuity; EAR checks; STEP_UP emits no permit; ALLOW produces action/context-bound clearance+permit refs.
- Status: `PRESERVED_WIRED`.

`execution_requirements.py::validate_execution_requirements` and subordinate checks
- `_causal_continuity`: exact state/causal continuity.
- `_authority_drift`: verified/current authority-state surface.
- `_multi_hop`: prior permit and reauthorization semantics.
- `_temporary_authority`: temporary authority bounded by expiry/scope.
- `_purpose_binding`: exact current purpose for protected actions.
- `_required_evidence`: evidence presence/status/freshness.
- `_reality_validation`: current reality evidence.
- `_verified_prior_outcome`: prior effect must be Veritas/WORM verified when required.
- `_impact_and_gates`: deterministic impact/reversibility + required gate policy.
- `_validate_gate_attestation`: exact actor/action/nonce/source/evidence/freshness binding.
- `_validate_governance_gate_profile`: explicit human/organizational review-completeness profile.
- `_replay_resistance`: execution sequence + nonce presence.
- `_resource_bounds`: requires declared bounds, but does not itself atomically meter consumption.
- Status: mostly `PRESERVED_WIRED`; resource consumption remains external.

`approver_authority.py::validate_approver_authority_gate`
- Purpose: prove independent approvers actually possess the relevant approval authority.
- Invariants: exact actors/capability/action/target/purpose/source/evidence/freshness, dual-control distinctness; approver evidence cannot mint execution authority.
- Status: `PRESERVED_WIRED` when EAR governance gates selected.

`confidential_execution.py::{validate_confidential_execution_continuity,substrate_binding_digest}`
- Purpose: exact confidential substrate continuity.
- Invariants: verified/current/non-revoked substrate, confidentiality/integrity/isolation, exact model/workload/measurement binding; no authority creation.
- Status: `PRESERVED_WIRED` under relevant execution profile.

`outcome_feedback.py::{validate_verified_prior_outcome,bind_verified_outcome_state}`
- Purpose: allow later REHT decisions to rely on proved prior execution state without treating observation as authority.
- Invariants: Veritas WORM verification, permit/clearance/package/entry bindings, acceptable outcome policy, `authority_granted=False`.
- Status: implementation `PRESERVED_WIRED` only if an upstream effect path actually produces the required Veritas/WORM outcome. Current production `EffectBoundary` does not do this automatically, therefore end-to-end status is `PARTIAL`.

## 2. Whiskers / local interrupt semantics

### valo-kernel

`contracts/uniform_whisker.py`
- `TransitionSurface`: INPUT, MODEL_OUTPUT, STATE_READ, STATE_WRITE, MEMORY_WRITE, DELEGATION, ROUTING, TOOL_REQUEST, EFFECT_COMMIT, EFFECT_RESULT, EVIDENCE_ADMISSION.
- `WhiskerMode`: SHADOW / ENFORCE.
- `WhiskerDisposition`: PASS / OBSERVE / STEP_UP / BLOCK.
- `WhiskerCostClass`: deterministic -> local semantic -> classifier -> model judge.
- `GovernedUniform`: portable governed context bound to exact consequence; explicitly `NO_AUTHORITY_CREATION`, cannot issue clearance or authorize execution.
- `TransitionObservation`: exact local transition observation.
- `WhiskerAssessment`: local evidence/control result.
- `WhiskerResult.is_binding_terminal`: ENFORCE + BLOCK/STEP_UP stops progression.
- `CallableWhisker.evaluate`: evaluator failures become BLOCK.
- `WhiskerCascade`: orders cheap probes first and stops at binding terminal.
- `uniform_freshness_whisker`: stale uniform -> BLOCK.
- `uniform_binding_whisker`: actor/action/state/consequence mismatch -> BLOCK.
- `default_uniform_whiskers`: standard cheap cascade.

`kernel/uniform.py::build_governed_uniform`
- Purpose: project Kernel context into a portable, attenuated uniform without state/authority creation.

Search result across Kernel/REHT/RACS/Gateway/Veritas/platform/Workflow ISA/Function Fabric/VAIG/BARO:
- `WhiskerCascade` and `default_uniform_whiskers` occur only in the contract and tests.
- `build_governed_uniform` occurs only in its module, work anchor and bridge test.

Current status: `PRESERVED_ORPHANED`.
This is the exact "værhår can stop but never allow" capability. The code exists; no production consequence-path wiring was found.

## 3. Production effect boundary after PR #38

### valo-reht `effect_boundary.py`

`PermitStore.consume_once`
- Required atomic single-use store; deployment must provide shared/durable semantics.

`InMemoryPermitStore`
- Explicitly test/single-process-development only.

`EffectBoundary.commit`
- Freezes exact action snapshot.
- Obtains execution context inside commit.
- Calls REHT itself.
- DENY/STEP_UP -> no effect.
- ALLOW requires permit and exact execution-context hash.
- Atomically consumes permit before effect.
- Failed invocation does not re-arm permit.
- Executes exact authorized action snapshot.

What it does not currently enforce:
- no mandatory whisker cascade before commit;
- no runtime-control-plane HALT/revocation input;
- no containment/runtime/environment/egress/credential/path-head binding;
- no physical boundary-only tool handle (accepts an arbitrary callable);
- no atomic resource-budget consumption;
- no mandatory execution receipt;
- no mandatory Veritas observation/WORM admission;
- no mandatory Kernel outcome event;
- no mandatory BARO/postcondition check;
- no active-session continuity/heartbeat/rollback/handover semantics.

Status: `PRESERVED_WIRED` for exact-action/context/single-use mechanics; `PARTIAL` as replacement for the former complete consequence path.

## 4. Gateway — non-authoritative but mechanically required semantics

### `gateway/core.py::ValoGateway.execute`
- Requires exactly one effect path.
- Tool path must expose boundary-only `_invoke_from_boundary`, otherwise `NO_DIRECT_EFFECT_PATH`.
- Revalidates authority, clearance, permit and exact bindings at execution time.
- Structural boundary replay must be READY.
- Applies `RuntimeControlPlane` before effect.
- Validates/consumes required resource reservations.
- Consumes permit before invocation.
- Produces success/failure `ExecutionReceipt` bound to action, authority, clearance, permit, executor, time, response, workspace, substrate and replay artifacts.
- Status versus new EffectBoundary: `PARTIAL`.

`gateway/core.py::_validate_binding`
- Execution-time authority/revocation, clearance freshness, workspace/substrate continuity, action/scope/capability/skill/binding checks.
- New EffectBoundary rebuilds fresh context and REHT-authorizes, which overlaps but has not been proven equivalent to every binding check.
- Status: `PARTIAL/UNPROVEN_EQUIVALENCE`.

### `gateway/control.py::RuntimeControlPlane`
- Events: REVOKE_AUTHORITY, REVOKE_PRINCIPAL, REVOKE_ACTOR, HALT_GLOBAL, HALT_SCOPE, RESUME_SCOPE, RESUME_GLOBAL.
- `apply`: updates mechanical interlock state.
- `assert_execution_allowed`: blocks global halt, revoked identities/authority, halted scope.
- Authority effect: none; can only narrow/stop.
- Current two-core effect path status: `MISSING`.

### `tool_adapters/base.py`
- `FunctionTool.invoke`: always raises `NO_DIRECT_EFFECT_PATH`.
- `_invoke_from_boundary`: only sealed boundary proof may call actual function.
- `ToolRegistry`: binds tool name/capability/target/credential reference; checks exact effect binding.
- Current EffectBoundary accepts arbitrary callable and therefore does not structurally prevent an alternate caller from invoking the same underlying tool elsewhere.
- Status: `MISSING` as a physical non-bypass invariant.

### `contracts/boundary.py`
- `BoundaryReplayInput`: canonical pinned action/contract/state/authority/evidence/decision/clearance/permit/governance-state/time bundle.
- `replay_effect_boundary`: fail closed on tampering, non-VALID governance basis, non-executable decision, stale/revoked authority/clearance/permit.
- Status: `PARTIAL`; action/context binding exists in new boundary, structural full-chain replay does not.

### `resource_budget.py`
- `required_resource_budget_ids`, `ResourceBudget`, `ResourceReservation`, `ConsumedResourceReservation`, `ResourceStateEvidence`, `ResourceBudgetLedger`.
- Invariants: parent/child budgets cannot widen; pending+committed hard limits; exact action/clearance/permit binding; atomic reservation/consume; resource-state evidence carries no authority.
- REHT only checks that resource limits are declared when required; it does not meter/consume them.
- Current status: `MISSING` on the simplified effect path when resource limits matter.

### `message_security.py`
- Authenticated governed message envelope, sender/recipient/purpose/workflow/origin-authority/delegation/scope/parent-lineage bindings and replay store.
- Child hop cannot widen authority scope.
- Current status: `NON_AUTHORITATIVE_REQUIRED` for inter-agent/message boundaries; not a universal effect-boundary concern, but not replaced by two-core either.

## 5. Containment / egress

### valo-platform `containment/gate.py`

`verify_containment_for_clearance`
- Missing/stale/expired/wrong-runtime/wrong-epoch -> DENY; breached/degraded or domain halt -> HALT.
- Evidence only; never authority.

`verify_execution_path`
- Exact action/runtime/environment/egress adapter/credential lease/path-head/attestation/epoch/lifetime binding.

`evaluate_egress`
- Only exact approved `ADAPTER` path may leave containment.
- Direct NETWORK/TOOL/CONNECTOR/CREDENTIAL paths deny by default.

Search shows these are used in tests/benchmarks but not imported by production REHT/EffectBoundary.
- Current status: `PRESERVED_ORPHANED` / effect-path `MISSING`.

### `containment/models.py`
- `ContainmentAttestationV1`: immutable runtime/environment/model/agent/harness/network/capability/connector/credential/adapter evidence.
- `ExecutionPathBindingV1`: exact runtime+adapter+credential+policy path for an action.
- `ContainmentViolationV1`: integrity-loss signal.
- `PermitRecordV1`, `CredentialLeaseRecordV1`: epoch-bound open capability/credential state.
- `SandboxEscapeReceiptV1`: records HALT, revocations, restart block, chain state and recommissioning.
- `ClearanceContainmentBindingV1`, `RACSPermitContainmentBindingV1`, `ExecutionReceiptContainmentV1`: carry the same containment/path digest across clearance -> permit -> receipt.
- `PacingDecisionV1`: may restrict scale, can never authorize execution.
- Status: `NON_AUTHORITATIVE_REQUIRED`; wiring into two-core path currently missing.

### `containment/controller.py::ContainmentDomainController`
- `register_permit`, `register_credential_lease`: epoch-bound only, blocked while halted.
- `emit_global_halt`: atomically HALT domain, revoke permits, invalidate credential leases, advance epoch, rotate restart token, preserve escape receipt.
- `is_restart_recovery_blocked`: restart cannot recover old execution capability.
- `recommission`: explicit human signature + strictly newer revocation epoch required to resume.
- Current status: `MISSING` from simplified effect path.

### `containment/receipts.py`
- `_bind`, `build_clearance_binding`, `build_racs_permit_binding`, `build_execution_receipt` maintain exact containment/path digest continuity across artifacts.
- Current status: `PRESERVED_ORPHANED` relative to the current two-core production path.

## 6. Veritas — evidence admission / immutability

### `execution.py::GatewayExecutionObservationV1`
- `verify`: strict schema/identity/action/permit/clearance/receipt/workspace/substrate/time/digest validation; `authority_granted` must be False.
- `to_observed_event`, `to_observation_package`: convert verified execution handoff into non-authoritative observed evidence.
- Current EffectBoundary does not produce equivalent mandatory handoff.
- Status: `MISSING` from mandatory production effect path.

### `worm.py::WORMLog`
- append-only hash chain; read/tail/verify; optional Ed25519 tail anchors; persistence refuses divergent or invalid historical rewrite.
- Authority effect: none.
- Status: `NON_AUTHORITATIVE_REQUIRED` when architecture promises durable tamper-evident execution evidence; no mandatory two-core wiring.

### `service.py::VeritasChainService`
- admits verified observations/negative evidence/completion/incident artifacts into WORM; tampered handoffs never enter storage.
- Current status: `PRESERVED_ORPHANED` relative to current EffectBoundary.

## 7. BARO — postcondition/reality observation

### `incident_poststate.py`
- `IncidentPostStateEvaluator.assess`: exact expected postcondition vs observed state; unhealthy/missing required observation sources -> INSUFFICIENT_EVIDENCE; first mismatch -> DIVERGED; otherwise MATCH.
- `_resolve`, `_timestamp`: deterministic field resolution/time validation.
- Explicitly does not authorize, execute or mutate state.
- Workflow ISA previously invoked BARO after Veritas observation before authoritative Kernel effect event.
- Current two-core EffectBoundary has no mandatory postcondition check.
- Status: `MISSING` from universal simplified effect path; component itself remains available.

## 8. RACS — deterministic cross-artifact/boundary integrity, not authority ownership

### `models.py`
- `ReasoningTraceBinding`: reasoning cannot grant authority.
- `GovernanceEvaluation`, `AdmissibilityDetermination`, `GovernanceClearance`: exact action/authority/delegation/policy/evidence/purpose/state/workspace/kernel/target/payload/connector/capability/consequence/reversibility/constraint/lifetime/revocation/evaluator bindings.

### `validation.py`
- `validate`, `check`, `_clearance_intra_check`: JSON schema + typed semantic conformance; ALLOW only for ADMISSIBLE/no constraints; MODIFY only conditionally admissible with enforceable constraints.

### `verification.py`
- `verify_evaluation_binding`: determination must bind exact evaluation/action/envelope and boundary assessment.
- `verify_clearance_binding`: clearance must bind exact determination and all authoritative digests; negative states cannot become clearable; validity/revocation/boundary chain required.
- Status: cross-artifact integrity `MISSING/PARTIAL` after narrowing to an internal `DecisionResult` unless equivalent digest continuity is proven elsewhere.

### `boundary_crossing.py`
- Boundary types: EXECUTION, DISCLOSURE, MANDATE, RESOURCE, EVALUATION.
- Boundary states: NO_CROSSING, AUTHORIZED, CONDITIONALLY_AUTHORIZED, UNAUTHORIZED, INDETERMINATE, STALE, REVOKED.
- Response floors: NONE, MODIFY, DEFER, STEP_UP, DENY, HALT.
- `BoundaryCrossing`: state change requires authorization binding; technical access alone is insufficient; unauthorized/resource/evaluation crossing rules fail closed.
- `BoundaryCrossingAssessment`: aggregate worst state/response/reasons and validity.
- `response_floor_satisfied`: ensures downstream response is at least as restrictive as required.
- REHT's narrowed three-state decision plane does not itself represent DEFER/MODIFY/HALT response floors.
- Status: `PARTIAL`; must be mapped to non-REHT control/continuity semantics rather than silently deleted.

### `boundary_validation.py`
- verifies evaluation/determination/clearance bindings; rejects dropped/injected boundary bindings or response-floor violations.
- Status: `MISSING/PARTIAL` on simplified path.

### Runtime continuity (`continuity.py`, `continuity_verification.py`)
- `GovernedCapabilityManifest`: telemetry, postconditions, timeout/retry, executor binding, supply-chain, reversibility/rollback requirements.
- `EnvironmentGovernanceProfile`: runtime limits, forbidden zones/resources, required telemetry/interlocks/human roles, fail-closed PAUSE/HALT policy.
- `GovernedExecutionSession`: exact action/authority/capability/environment/evaluation/REHT/RACS/permit/executor/deadline/heartbeat/sequence binding.
- `RuntimeObservation`: SENSOR/CONTROLLER/CONNECTOR/DESTINATION/WATCHER/HUMAN/etc signals, quality/freshness/integrity.
- `ContinuityDecision`: CONTINUE, MODIFY_RUNTIME_BOUNDS, PAUSE, STOP, REAUTHORIZE, ROLLBACK, HANDOVER, HALT.
- `InterventionReceipt`, `RecoveryPlan`, `RecoveryReceipt`: applied intervention/recovery evidence; recovery plan explicitly carries no execution authority; failed recovery leaves HALTED.
- `verify_execution_session`: exact artifact chain/currentness/executor/capability/consequence/deadline.
- `prove_runtime_bounds_narrowing`: runtime modification may only provably narrow; unknown/ambiguous changes fail closed.
- `verify_continuity_decision`: exact session/sequence/action/capability/environment/authority binding + narrowing proof.
- Current two-core effect path has no active-session continuity loop.
- Status: `MISSING` as runtime-continuity function family.

### `normative_receipt.py::BoundaryDecisionReceiptV02`
- DEFER/STEP_UP non-execution receipt with `execution_occurred=False`, `clearance_issued=False`, `commit_token_issued=False`; binds research/VAIG/REHT evidence.
- Status: `NON_AUTHORITATIVE_REQUIRED` when such decision evidence is needed; not an authority core.

## 9. Workflow ISA — orchestration invariants that surround consequence

### `ports/boundaries.py`
- Original `DecisionResult` broader comment plane plus Kernel/Reht/Gateway/Veritas/BARO ports.
- Moving `DecisionResult/RehtPort` into REHT is mechanically safe only for the type boundary; it does not replace the other port semantics.

### `compiler/compiler.py::compile_graph`
Fail-closed compile-time invariants:
- valid opcode/node-class/effect declaration;
- reachability/ref/input/output/type safety;
- no WRITE without authority policy;
- irreversible WRITE requires idempotency;
- no probabilistic output directly into WRITE;
- cycle must have termination semantics;
- HALT cannot have forward successors.
- Status: `OUT_OF_RUNTIME` but semantically required for compiled workflows; not replaced by Kernel+REHT.

### `effects/system.py`
- `IRREVERSIBLE_EFFECTS`, `EXTERNAL_EFFECTS`, `allowed_effects`, `validate_effect` classify consequence and constrain which node classes may carry it.
- Status: `OUT_OF_RUNTIME/NON_AUTHORITATIVE_REQUIRED` for workflow programs.

### `runtime/engine.py`
- deterministic readiness/path semantics;
- explicit HALT/DEFER/COMPENSATE;
- retry safety: irreversible WRITE after uncertain outcome requires verify/reconcile instead of blind replay;
- output refinements may only be attached by opcodes that proved them;
- unexpected handler failure fails closed.
- Status: orchestration semantics remain in Workflow ISA, but no longer part of REHT dependency graph. They must not be described as redundant.

### `stdlib/handlers.py`
- `_authorization`: fresh Kernel context -> REHT; rejects non-ALLOW, missing permit/clearance or context hash mismatch; derives deterministic execution binding.
- `_execution`: Gateway -> Veritas -> BARO -> Kernel event; Gateway failure never emits verified effect or authoritative Kernel transition.
- `_write_pipeline`: full consequence path.
- `_reconcile`: probabilistic output must be explicitly admitted before verified use.
- `_prepare_action`, `_authorize_action`, `_execute_action`, resource/deadline handlers: action preparation and governed WRITE.
- Current simplified EffectBoundary replaces only a subset of `_authorization + Gateway` and omits mandatory Veritas/BARO/Kernel completion semantics.
- Status: `PARTIAL` replacement.

### `patterns/incident.py::build_governed_incident_graph`
- unhealthy evidence source -> HALT;
- probabilistic severity kept away from WRITE;
- live path requires authorization, execution, verified poststate.
- Status: application pattern remains, but assumes full consequence path semantics.

## 10. Function Fabric — compile-time governance monotonicity

### `compiler/governance.py::check_governance_monotonicity`
- parent risk cannot be below child max;
- parent authority covers child capability+scope;
- evidence type/status cannot weaken;
- rights/purpose cannot disappear;
- parent autonomy cannot expand beyond children.
- Helpers `_authority_covered`, `_evidence_covered`, `_rights_covered`, `_purpose_covered` implement exact coverage semantics.
- Authority effect: none.
- Status: `OUT_OF_RUNTIME/NON_AUTHORITATIVE_REQUIRED`.

### `compiler/effects.py`
- `leaf_effects_within_declared`: workflow cannot carry undeclared effects.
- `parent_effects_cover_children`: composite function cannot hide child effects.
- `compiled_effect_set`: exact effect inventory.
- Status: `OUT_OF_RUNTIME/NON_AUTHORITATIVE_REQUIRED`.

### `contracts/function.py`
- typed FunctionDefinition: inputs/outputs/workflow, pre/postconditions, declared effects, risk, autonomy, authority/evidence/rights/purpose/jurisdiction, reversibility/idempotency.
- Status: `OUT_OF_RUNTIME`; feeds governance metadata, not an authority engine.

## 11. Action Attestation Service — trust-boundary normalization

### `core.py::AttestationRecord`
- immutable signed record; payload/action/nonce fingerprint, HMAC, expiry, prior hash, serialization.
- Status: `NON_AUTHORITATIVE_REQUIRED` for trusted evidence path.

### `authority_adapter.py::AuthorityAttestationAdapter`
- accepts only verified source facts; forbids authorization/permit/clearance outputs; normalizes standing/continuity/session integrity/drift/freshness/evidence into `AuthorityStateV1`.
- `attest` signs normalized state.
- Status: `NON_AUTHORITATIVE_REQUIRED`.

### `gate_adapter.py::GateAttestationAdapter`
- normalizes human/dual-control/confirmation/step-up/delay gate facts.
- forbids authorization outputs.
- binds actor/action hash/execution nonce/source/key/evidence/freshness.
- independent approver gates may carry verified approver-authority facts but those facts cannot emit execution authority.
- dual control requires distinct approvers and distinct authority refs.
- `attest`, `verify_attested` provide signed-record path.
- Status: `PRESERVED_WIRED` through REHT EAR gate validation when supplied.

### `reht_gate_context.py::build_reht_gate_context`
- accepts only records signed by caller-owned trusted current keys; validates signing-time/current-time validity and revocation; maps verified gate records into REHT context.
- Status: `PRESERVED_WIRED` as an adapter when used; no authority creation.

### `ledger.py::Ledger`
- JSONL + SQLite append path; unique `(tenant_id,action_id)` replay protection; fsync; WORM-intended query store.
- Status: evidence infrastructure, not authority.

## 12. VAIG — diagnostic/materiality evidence, not authority

### `guard.py::BlindspotGuard`
- model-backed measurements with self-judging/low confidence are downgraded to UNCALIBRATED; disagreement reduces trust rather than silently becoming certainty.
- Status: `NON_AUTHORITATIVE_REQUIRED` when VAIG evidence is used.

### `continuity_assessment.py::assess_continuity_request`
- validates digest-bound continuity request, exact baseline/source coverage, trigger evidence/freshness/integrity and classifies materiality.
- Module explicitly does not issue clearance/permit or authorization outcomes.
- Status: `NON_AUTHORITATIVE_REQUIRED` continuity evidence provider.

### `continuity_wire.py::assess_continuity_wire`
- strict wire envelope + assessed-at checkpoint validation.
- Status: adapter.

### `why_gate.py`
- `decide_why`, `evaluate_why`, receipt/chain verification produce CONTINUE/WATCH/HUMAN_REVIEW/HALT from weakest-link score.
- This module predates/currently coexists with the stricter principle that model/diagnostic evidence cannot itself grant authority. Whether its HALT is an advisory/control signal or direct runtime interlock must be explicitly resolved; no silent promotion to REHT authority is allowed.
- Status: `UNKNOWN/POTENTIAL_CONTROL_SIGNAL`; requires wiring audit before architectural decision.

## 13. Confirmed preservation failures / unresolved mappings

1. `WhiskerCascade` enforce-mode STOP semantics: `PRESERVED_ORPHANED`.
2. Gateway `RuntimeControlPlane` global/scoped HALT/revoke: `MISSING` from current EffectBoundary.
3. Containment domain HALT + permit/credential revocation + restart-block + human recommission: `MISSING`.
4. Physical `NO_DIRECT_EFFECT_PATH` tool interlock: `MISSING` in EffectBoundary API.
5. Containment runtime/environment/egress/credential/path-head binding: `MISSING`.
6. Atomic resource-budget reservation/consumption: `MISSING` where required.
7. Mandatory success/failure execution receipt: `MISSING`.
8. Mandatory Veritas verified handoff + WORM admission: `MISSING`.
9. Mandatory effect observation back into Kernel: `MISSING`.
10. Mandatory BARO/postcondition verification before declaring valid completion: `MISSING`.
11. RACS boundary response-floor/cross-artifact continuity: `PARTIAL/MISSING`.
12. RACS active-session continuity (heartbeat/PAUSE/STOP/REAUTHORIZE/ROLLBACK/HANDOVER/HALT): `MISSING`.
13. Workflow uncertain-effect retry/reconcile semantics: not a REHT concern; must remain in orchestrators and must not be called redundant.
14. Function Fabric governance monotonicity: compile-time required, independent of runtime core.
15. Persistent-state admission and authority projection/revocation-assurance: Kernel-side required semantics, independent of runtime core.

## Working architectural conclusion

`Kernel + REHT` is defensible only as the two **authoritative ownership cores**:
- Kernel owns operative/canonical state.
- REHT owns execution authorization.

It is not yet defensible as the complete execution architecture.

The complete system still requires subordinate, non-authoritative semantics for:
- local sensing/interrupts;
- control-plane halt/revocation;
- containment and physical egress interlocks;
- exact effect-path binding;
- resource budgets;
- execution receipts and immutable evidence;
- postcondition/reality verification;
- active-session continuity/recovery;
- compile-time governance/effect monotonicity.

No architecture component may be removed until its symbols are mapped to one of these destinations with a proven preservation status.
