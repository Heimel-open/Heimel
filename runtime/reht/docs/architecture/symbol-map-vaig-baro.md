# VAIG / BARO semantic symbol map

Status: COMPLETE for execution-governance relevance
Date: 2026-08-23
Audit base: `5ecf09f2ef94c83a04b10a7ef4bcf3becc92a32d`

This map classifies the VAIG and BARO code paths that can be mistaken for, constrain, observe, or feed execution governance. The classification is by function, not component name.

## VAIG — current bounded evaluation path

### `vaig/evaluation_report.py`

`EvaluationReport`
- Hash-bound, replayable VAIG -> REHT evaluation record.
- `execution_authority=False` and `requires_reht_clearance=True` are part of integrity verification.
- Missing/failed/uncalibrated measurements remain explicit status, never silent low risk.
- Status: `PRESERVED_WIRED / NON_AUTHORITATIVE_REQUIRED`.

`build_evaluation_report`
- Packages orchestrator measurements, abstentions, evidence blocks, errors, underdetermination and tradecraft.
- Produces rejection reasons but never clearance.
- Status: `PRESERVED_WIRED`.

### `vaig/normative_governance.py`

`NormativeHandoffDisposition`
- Only `NO_OVERRIDE | DEFER | STEP_UP`.
- Deliberately cannot manufacture `ALLOW` or `MODIFY`.

`NormativeGovernanceHandoffV1`
- `execution_authority=False`, `requires_reht_clearance=True` enforced at construction.
- `NO_OVERRIDE` explicitly means no extra restriction, not ALLOW.
- `DEFER/STEP_UP` can narrow/block ordinary clearance.
- Status: `PRESERVED_WIRED / CORRECT_SUBORDINATION`.

`NormativeGovernanceGateV1.evaluate`
- Maps research/evaluator independence and unresolved normative conflict into bounded restriction.
- Never grants authority.
- Status: `PRESERVED_WIRED`.

### `vaig/security_pipeline.py`

`SecurityObservation`, `SecurityEvidencePackage`, `DefenceInDepthPipeline`
- Security observation/evidence only.
- `to_reht_evidence()` emits measurements/digests, no execution verdict or authority.
- Status: `PRESERVED / NON_AUTHORITATIVE_REQUIRED when consumed`.

### `vaig/aaec_trajectory.py`

AAEC trajectory evaluator
- Validates RACS AAEC trajectory inputs, lineage, observation evidence and response floors.
- Can emit an evaluation recommendation in the six-outcome vocabulary.
- Explicitly never establishes authority, issues REHT clearance, creates a permit or executes an effect.
- Rejects RACS validation carrying execution authority.
- Status: `PRESERVED / NON_AUTHORITATIVE_REQUIRED`.

### `vaig/judge/multiverse.py`

`JudgeMultiverse`
- Runs judge configurations, measures spread/disagreement and abstains on divergence.
- AARM vocabulary is used as an evaluation label for comparison only.
- Status: `OUT_OF_RUNTIME / EVALUATION_ASSURANCE`.

### Existing VAIG evidence/control families already mapped

- `vaig/guard.py`: fail-closed evidence/model-instrument validity.
- `vaig/why_gate.py`: rationale/risk evidence.
- `vaig/continuity_assessment.py`: continuity/materiality evaluation, no authority.
- `vaig/continuity_wire.py`: bounded continuity handoff.
- `vaig/transition_risk.py`: transition risk evidence.
- `vaig/orchestrator.py`: evaluation orchestration.
- `vaig/agent_loop/gate.py`, `vaig/agent_loop/loop.py`: currently consume AARM and therefore inherit the AARM authority conflict described below.

## VAIG — legacy authority conflicts

### `vaig/aarm.py`

`AARMVerdict`
- `ALLOW | MODIFY | DEFER | DENY | STEP_UP | HALT`.
- Module explicitly declares these the six **authoritative** verdicts and AARM the single source of truth for governed boundary-crossing verdicts.
- Semantics explicitly describe ALLOW/MODIFY as execution outcomes.

`AARMAuthorityEnvelope`
- Carries actor/action/expiry authority-like bounds inside VAIG.

`verdict_from_evidence`
- Converts evidence directly into AARM verdict.

`aarm_decide`
- Pure deterministic decision engine that can return ALLOW/MODIFY directly from risk/evidence conditions.
- Status: `LEGACY_AUTHORITY_CONFLICT`.
- Blocking invariant: REHT must be the sole owner of execution authorization. AARM may survive only as evaluation/recommendation or restrictive floor, never clearance/permit authority.

### `vaig/api.py`

`POST /api/v1/authorize`
- Calls `verdict_from_evidence` directly.
- API documentation calls the result an authorization decision and describes ALLOW/MODIFY as execute outcomes.
- Does not require a verified REHT GovernanceClearance before returning the decision.
- Status: `LEGACY_AUTHORITY_CONFLICT / DIRECT_BYPASS_SURFACE`.

`GET /api/v1/authorization/{decision_id}`
- Represents prior AARM decision as an authorization record.
- Status: `LEGACY_AUTHORITY_SEMANTICS`.

### `src/authority_gate.py`

`AuthorityDecision`
- `ALLOW | STEP_UP | DEFER | DENY | HALT`.

`AuthorityDelegation`
- Own local delegation object with validity/scope/context/value/cost semantics.

`AuthorityStore`, `InMemoryAuthorityStore`
- Own delegation creation, lookup, update and revocation state.

`AuthorityGate.check_authority`
- Explicitly sits between VACS signals and execution.
- Independently evaluates delegation/context/value/cost/emergency threshold and can return ALLOW.
- Status: `LEGACY_AUTHORITY_CONFLICT`.

`AuthorityGate.create_delegation`
- Creates local authority state outside canonical Kernel authority ownership.
- Status: `LEGACY_STATE_OWNERSHIP_CONFLICT`.

### `vacs/src/policy_engine.py`

`Decision`, `ACSPolicyEngine.evaluate`
- Six-outcome policy evaluation including ALLOW.
- By itself would be ambiguous, but current execution adapter explicitly treats this as evaluation only.
- Status: `PRESERVED_AS_EVALUATION`, conditional on never being consumed as clearance elsewhere.

### `vacs/src/clearance.py`

`GovernanceClearance`, `verify_clearance`
- Correct architecture statement: VAIG evaluates, REHT clears.
- Only `VALID` REHT clearance may permit READY.
- Structural reference verifier; signature verification is delegated to REHT layer.
- Status: `CORRECT_SUBORDINATION / REFERENCE_CONTRACT`.

### `vacs/src/execution_adapter.py`

`ExecutionHandoffAdapter.prepare`
- Recomputes VACS evaluation, requires evaluation ALLOW, then separately requires verified REHT GovernanceClearance.
- No REHT clearance -> BLOCKED.
- Does not itself execute external side effects.
- Status: `PRESERVED / DESIRED_HANDOFF_SEMANTICS`.

## VAIG — local optimization/resource controls

### `src/roi_gate.py`

`ROIGate.evaluate`
- Pre-execution expected-value calculation with local `ALLOW/STEP_UP/DENY` vocabulary.
- No external effect or canonical authority state.
- Correct role: evidence/recommendation or restrictive policy input to REHT.
- Status: `SEMANTIC_COLLISION`; not an authority blocker if kept evaluation-only.

### `src/spend_gate.py`

`SpendGate.authorize`
- Budget/resource policy with `ALLOW/STEP_UP/DEFER/DENY/HALT` vocabulary.
- Records spend in its local accounting state after local ALLOW.
- Correct role: resource budget evidence/reservation policy, subordinate to REHT and the mechanical resource ledger.
- Status: `SEMANTIC_COLLISION / RESOURCE_CONTROL`; must not be execution authority.

### `src/model_router.py`

`ModelRouter.route`
- Chooses cheapest adequate model and returns local `ALLOW/STEP_UP/DENY` routing result.
- Correct role: model-selection routing only.
- Status: `SEMANTIC_COLLISION / OUT_OF_AUTHORITY`.

### `src/efficiency_engine.py`

`EfficiencyEngine`
- Post-execution outcome/value measurement and learning signal generation.
- No execution authorization.
- Status: `OUTCOME_EVIDENCE / OUT_OF_AUTHORITY`.

### `src/value_weighting.py`

`ValueWeighting`
- Cross-domain value normalization.
- No execution authorization.
- Status: `EVALUATION_SUPPORT / OUT_OF_AUTHORITY`.

### `src/reward_economy.py`

`RewardEconomy`
- Explicitly EXPERIMENTAL/outside VAIG Core.
- Token/reward bookkeeping, not execution governance.
- Status: `OUT_OF_RUNTIME`.

## Final VAIG classification

There are two architectures coexisting in the repo:

1. Current/correct: VAIG produces bounded evidence/evaluation/restrictions; REHT alone clears execution.
2. Legacy/conflicting: AARM + `/api/v1/authorize` + `src/authority_gate.py` claim or implement execution authorization independently.

The second family blocks any claim that the portfolio already has one unambiguous authorization owner.

## BARO — evidence-only observation surface

### `src/valo_baro/core/reality_package.py`

`RealityPackage`
- Canonical BARO evidence envelope.
- Explicitly never authorizes, blocks or decides.
- Construction rejects observed-signal keys whose words imply authorization, block, decision, admission, clearance, permit, approval or deny.
- Status: `PRESERVED / STRONG_EVIDENCE_ONLY_BOUNDARY`.

### `src/valo_baro/attention_whiskers.py`

`DetectionSensorEvaluator.evaluate`
- Cheap attention routing from regime drift / consequence / authority distance / evidence gap.
- GREEN/YELLOW/ORANGE/RED route to deeper or lighter evaluation.
- Explicitly GREEN != ALLOW and RED != DENY; `authority="none"`.
- Status: `PRESERVED / ADVISORY_ONLY`.
- Important distinction: these BARO detection sensors are not Kernel `uniform_whisker` ENFORCE interlocks.

### `src/valo_baro/evidence_loop.py`

`EvidenceLoopEvaluator.assess`
- Correlates REHT authorization with Veritas observations and completed evidence.
- Emits evidence collection requests, evidence classification, first observed deviation and escalation reasons.
- Explicitly does not authorize, enforce or execute.
- Status: `PRESERVED / POST_EFFECT_EVIDENCE`.

### `src/valo_baro/incident_poststate.py`

- Poststate / reality verification family mapped previously.
- Detects expected-vs-observed divergence and packages outcome evidence.
- Status: `PRESERVED_ORPHANED` relative to simplified `EffectBoundary`, because the effect path does not invoke it mandatorily.

### `src/valo_baro/baro_observability_convergence.py`

`BaroObservabilityConvergence`
- Converges SPI/narrative observations through FETCHED -> NORMALIZED -> SCORED -> INTERPRETED -> ROUTED -> RECEIPTED.
- Routes attention only, never action authorization.
- Status: `PRESERVED / OBSERVATION_ONLY`.

### `src/valo_baro/api.py`

- Observation, routing and health endpoints only.
- No execution-authority endpoint found.
- Some endpoint examples are synthetic/demo records, which is an evidence-quality concern but not an authority conflict.
- Status: `OUT_OF_AUTHORITY`.

### `src/valo_baro/falsification.py`

- Offline falsification/backtest harness for BARO observation claims.
- No runtime authorization.
- Status: `OUT_OF_RUNTIME / RESEARCH_ASSURANCE`.

## Final BARO classification

No BARO execution-authority implementation was found in the audited source paths or authority/authorize searches. BARO is correctly an observation/evidence layer.

The architectural defect is downstream wiring: verified post-effect observation/evidence is not mandatory on the simplified consequence path. BARO itself is not the authority problem.
