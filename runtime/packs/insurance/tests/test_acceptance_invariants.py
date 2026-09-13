from datetime import timedelta
from uuid import uuid4

from examples.mock_erp import MockErpSapTool
from valo_insurance_pack.claims.verifier import verify_claims_evidence_pack
from valo_insurance_pack.contracts.assurance_profile import (
    AssuranceProfileV1,
    ConsequenceClass,
    EffectivePeriod,
    FailureOutcome,
)
from valo_insurance_pack.contracts.evaluation import AssuranceResult
from valo_insurance_pack.contracts.source_evidence import (
    ChangedSinceStatus,
    RevocationVisibilityStatus,
    SourceAssuranceEvidenceV1,
)
from valo_insurance_pack.evaluation.evaluator import evaluate_commit_assurance
from valo_insurance_pack.pipeline.procurement_scenario import (
    GovernedProcurementPipeline,
)
from valo_insurance_pack.profiles.carrier_examples import (
    PROCUREMENT_HIGH_RISK,
    PROCUREMENT_STANDARD,
)
from valo_insurance_pack.utils.crypto import sha256_digest, utcnow


def _mock_reht_authorizer(action: dict) -> dict:
    return {
        "clearance_id": f"clr-{uuid4()}",
        "action_digest": sha256_digest(action),
        "authority_envelope_id": f"auth-{uuid4()}",
        "decision_contract": {
            "decision": "ALLOW",
            "principal_id": "principal:user-1",
            "actor_id": "agent:worker-1",
            "action_type": action.get("action_type", "PROCUREMENT_ORDER_CREATE"),
            "target": action.get("target", "erp:sap/po/create"),
        },
        "decided_at": utcnow().isoformat(),
        "valid_until": (utcnow() + timedelta(minutes=5)).isoformat(),
        "reht_ref": f"reht-{uuid4()}",
    }


def _mock_gateway_executor(*, action: dict, clearance: dict, tool, now=None) -> dict:
    now = now or utcnow()
    tool_resp = tool.invoke(action.get("parameters", {}))
    return {
        "execution_id": f"exec-{uuid4()}",
        "permit_id": f"permit-{uuid4()}",
        "clearance_id": clearance["clearance_id"],
        "action_digest": sha256_digest(action),
        "executor_id": "agent:worker-1",
        "started_at": now.isoformat(),
        "completed_at": now.isoformat(),
        "status": "succeeded",
        "response_digest": sha256_digest(tool_resp),
        "tool_response": tool_resp,
    }


def _mock_veritas_recorder(exec_output: dict) -> dict:
    return {
        "schema": "valo.gateway.execution-observation.v1",
        "package_id": f"obs-pkg-{exec_output.get('execution_id', 'unknown')}",
        "execution_id": exec_output.get("execution_id", "unknown"),
        "permit_id": exec_output.get("permit_id", "unknown"),
        "clearance_id": exec_output.get("clearance_id", "unknown"),
        "action_digest": exec_output.get("action_digest", "unknown"),
        "observation_digest": sha256_digest(exec_output),
        "recorded_at": utcnow().isoformat(),
        "worm_sequence": 1,
    }


def test_assurance_profile_swappable_without_reht_change():
    """AssuranceProfile can be swapped (Standard vs High Risk) without altering REHT."""
    now = utcnow()
    tool = MockErpSapTool()

    action = {
        "action_type": "PROCUREMENT_ORDER_CREATE",
        "target": "erp:sap/po/create",
        "parameters": {"po_number": "PO-SWAP-1", "amount": 8000},
    }

    # Standard sources (sufficient for STANDARD, insufficient for HIGH_RISK)
    standard_sources = [
        SourceAssuranceEvidenceV1(
            source_id="entra_id",
            subject="user:alice",
            observed_at=now - timedelta(seconds=100),
            attestation_type="OIDC_HARDWARE_MFA",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
        ),
        SourceAssuranceEvidenceV1(
            source_id="erp_sap_budget",
            subject="budget:cc-1",
            observed_at=now - timedelta(seconds=200),
            attestation_type="ERP_AUTHORITATIVE_API",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
        ),
    ]

    # 1. Under Standard Profile -> Satisfied & Executes
    pipeline_std = GovernedProcurementPipeline(
        profile=PROCUREMENT_STANDARD,
        reht_authorizer=_mock_reht_authorizer,
        gateway_executor=_mock_gateway_executor,
        veritas_recorder=_mock_veritas_recorder,
        policy_reference="pol-acceptance-test",
    )
    res_std = pipeline_std.run(
        action=action, source_evidences=standard_sources, tool=tool, now=now
    )
    assert res_std.success
    assert "PO-SWAP-1" in tool.committed_pos

    # 2. Swap to High Risk Profile -> Fails closed without modifying REHT
    pipeline_risk = GovernedProcurementPipeline(
        profile=PROCUREMENT_HIGH_RISK,
        reht_authorizer=_mock_reht_authorizer,
        gateway_executor=_mock_gateway_executor,
        veritas_recorder=_mock_veritas_recorder,
        policy_reference="pol-acceptance-test",
    )
    res_risk = pipeline_risk.run(
        action=action, source_evidences=standard_sources, tool=tool, now=now
    )
    assert not res_risk.success
    assert res_risk.assurance_evaluation.assurance_result == AssuranceResult.UNMET
    assert any(
        "missing_required_source: required authoritative source 'compliance_dual_control'"
        in u
        for u in res_risk.assurance_evaluation.unmet_requirements
    )


def test_source_evidence_upgradeable_without_reht_semantics_change():
    """P1 test: Source can be upgraded from timestamp -> version check -> event cursor, satisfying minimums."""
    now = utcnow()

    # Profile requiring version pinning
    profile_req_version = AssuranceProfileV1(
        profile_id="prof-version-req",
        insurer_reference="carrier:test",
        coverage_condition_ref="cond-1",
        action_type="PO_CREATE",
        consequence_class=ConsequenceClass.HIGH,
        required_authoritative_sources=["erp_source"],
        minimum_assurance_per_source={"erp_source": "VERSION_PINNED"},
        failure_outcome=FailureOutcome.DENY,
        effective_period=EffectivePeriod(
            effective_from=now - timedelta(days=1),
            effective_until=now + timedelta(days=365),
        ),
    )

    # Level 1: Simple timestamp evidence (Rank 10)
    ev_level1 = SourceAssuranceEvidenceV1(
        source_id="erp_source",
        subject="po:PO-UPGRADE-1",
        observed_at=now - timedelta(seconds=10),
        attestation_type="BASIC_TIMESTAMP",
        revocation_visibility=RevocationVisibilityStatus.ACTIVE,
        changed_since_status=ChangedSinceStatus.UNCHANGED,
    )

    # Level 2: Upgraded with version pinning (Rank 20)
    ev_level2 = SourceAssuranceEvidenceV1(
        source_id="erp_source",
        subject="po:PO-UPGRADE-1",
        observed_at=now - timedelta(seconds=10),
        source_version="v2.4.0",
        version_cursor="vcursor-9081",
        attestation_type="VERSION_PINNED",
        revocation_visibility=RevocationVisibilityStatus.ACTIVE,
        changed_since_status=ChangedSinceStatus.UNCHANGED,
    )

    # Level 3: Upgraded with event stream cursor and cryptographic attestation (Rank 30)
    ev_level3 = SourceAssuranceEvidenceV1(
        source_id="erp_source",
        subject="po:PO-UPGRADE-1",
        observed_at=now - timedelta(seconds=10),
        source_version="v2.4.0",
        version_cursor="vcursor-9081",
        event_cursor="event-stream-109485",
        revocation_visibility=RevocationVisibilityStatus.ACTIVE,
        changed_since_status=ChangedSinceStatus.UNCHANGED,
        attestation_type="EVENT_STREAM_CURSOR",
        provenance={"signing_key_id": "sap-hsm-key-4", "cluster": "eu-central-1"},
    )

    # Level 1 fails against VERSION_PINNED minimum
    eval_lvl1 = evaluate_commit_assurance(
        profile=profile_req_version,
        action={"action_type": "PO_CREATE"},
        source_evidences=[ev_level1],
        now=now,
    )
    assert not eval_lvl1.is_satisfied
    assert any(
        "insufficient_assurance_capabilities" in u for u in eval_lvl1.unmet_requirements
    )

    # Level 2 meets VERSION_PINNED minimum
    eval_lvl2 = evaluate_commit_assurance(
        profile=profile_req_version,
        action={"action_type": "PO_CREATE"},
        source_evidences=[ev_level2],
        now=now,
    )
    assert eval_lvl2.is_satisfied

    # Level 3 (EVENT_STREAM_CURSOR) is strictly stronger and meets VERSION_PINNED minimum
    eval_lvl3 = evaluate_commit_assurance(
        profile=profile_req_version,
        action={"action_type": "PO_CREATE"},
        source_evidences=[ev_level3],
        now=now,
    )
    assert eval_lvl3.is_satisfied


def test_no_non_allow_path_can_yield_consequence():
    """No non-ALLOW path (DENY, STEP_UP, DEFER, HALT) can ever execute an ERP consequence."""
    now = utcnow()

    for failure_outcome in [
        FailureOutcome.DENY,
        FailureOutcome.STEP_UP,
        FailureOutcome.DEFER,
        FailureOutcome.HALT,
    ]:
        tool = MockErpSapTool()
        profile = AssuranceProfileV1(
            profile_id=f"prof-{failure_outcome.value}",
            insurer_reference="carrier:test",
            coverage_condition_ref="cond-test",
            action_type="PO_CREATE",
            consequence_class=ConsequenceClass.HIGH,
            required_authoritative_sources=["source_a"],
            failure_outcome=failure_outcome,
            effective_period=EffectivePeriod(
                effective_from=now - timedelta(days=1),
                effective_until=now + timedelta(days=365),
            ),
        )

        pipeline = GovernedProcurementPipeline(
            profile=profile,
            reht_authorizer=_mock_reht_authorizer,
            gateway_executor=_mock_gateway_executor,
            veritas_recorder=_mock_veritas_recorder,
            policy_reference="pol-acceptance-test",
        )
        action = {
            "action_type": "PO_CREATE",
            "parameters": {"po_number": f"PO-{failure_outcome.value}"},
        }

        # Pass empty evidence to trigger the failure outcome
        result = pipeline.run(action=action, source_evidences=[], tool=tool, now=now)

        assert not result.success
        assert len(tool.committed_pos) == 0
        assert len(tool.invocations) == 0


def test_claims_evidence_pack_deterministic_reconstruction():
    """ClaimsEvidencePack deterministically reconstructs why action had effect."""
    now = utcnow()
    tool = MockErpSapTool()
    pipeline = GovernedProcurementPipeline(
        profile=PROCUREMENT_STANDARD,
        reht_authorizer=_mock_reht_authorizer,
        gateway_executor=_mock_gateway_executor,
        veritas_recorder=_mock_veritas_recorder,
        policy_reference="pol-acceptance-test",
    )

    action = {
        "action_type": "PROCUREMENT_ORDER_CREATE",
        "target": "erp:sap/po/create",
        "parameters": {"po_number": "PO-RECONSTRUCT-1", "amount": 1000},
    }
    sources = [
        SourceAssuranceEvidenceV1(
            source_id="entra_id",
            subject="user:alice",
            observed_at=now - timedelta(seconds=10),
            attestation_type="OIDC_HARDWARE_MFA",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
        ),
        SourceAssuranceEvidenceV1(
            source_id="erp_sap_budget",
            subject="budget:cc-1",
            observed_at=now - timedelta(seconds=20),
            attestation_type="ERP_AUTHORITATIVE_API",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
        ),
    ]

    res = pipeline.run(action=action, source_evidences=sources, tool=tool, now=now)
    assert res.success
    pack = res.claims_pack

    # Offline verifier reconstructs and validates the entire chain
    report = verify_claims_evidence_pack(pack)
    assert report.is_valid
    assert len(report.errors) == 0
    assert pack.commit_time_evaluation.is_satisfied


def test_insurance_layer_cannot_authorize_execution():
    """Assurance evaluation by itself NEVER issues permits or grants execution authority."""
    now = utcnow()
    profile = PROCUREMENT_STANDARD
    action = {"action_type": "PROCUREMENT_ORDER_CREATE", "target": "erp:sap/po/create"}
    sources = [
        SourceAssuranceEvidenceV1(
            source_id="entra_id",
            subject="user:alice",
            observed_at=now,
            attestation_type="OIDC_HARDWARE_MFA",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
        ),
        SourceAssuranceEvidenceV1(
            source_id="erp_sap_budget",
            subject="budget:cc-1",
            observed_at=now,
            attestation_type="ERP_AUTHORITATIVE_API",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
        ),
    ]

    eval_result = evaluate_commit_assurance(
        profile=profile,
        action=action,
        source_evidences=sources,
        now=now,
    )

    assert eval_result.is_satisfied
    # Crucial invariant: evaluation result has no permit, no execution grant
    assert not hasattr(eval_result, "permit")
    assert not hasattr(eval_result, "execution_token")
    assert not hasattr(eval_result, "authorize_execution")
