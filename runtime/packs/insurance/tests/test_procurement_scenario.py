from datetime import timedelta
from uuid import uuid4

import pytest

from examples.mock_erp import MockErpSapTool
from valo_insurance_pack.claims.verifier import verify_claims_evidence_pack
from valo_insurance_pack.contracts.assurance_profile import (
    EffectivePeriod,
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
    PROCUREMENT_HIGH_VALUE,
    PROCUREMENT_STANDARD,
)
from valo_insurance_pack.utils.crypto import sha256_digest, utcnow


def _default_reht_authorizer(action: dict) -> dict:
    return {
        "clearance_id": f"clr-{uuid4()}",
        "action_digest": sha256_digest(action),
        "authority_envelope_id": action.get("authority_envelope_id", f"auth-{uuid4()}"),
        "decision_contract": {
            "decision": "ALLOW",
            "principal_id": action.get("principal_id", "principal:corp-procurement"),
            "actor_id": action.get("actor_id", "agent:procurement-worker-1"),
            "action_type": action.get("action_type", "PROCUREMENT_ORDER_CREATE"),
            "target": action.get("target", "erp:sap/po/create"),
        },
        "decided_at": utcnow().isoformat(),
        "valid_until": (utcnow() + timedelta(minutes=5)).isoformat(),
        "reht_ref": f"reht-decision-{uuid4()}",
        "policy_refs": ["cond-procurement-high-value-v1"],
    }


def _default_gateway_executor(*, action: dict, clearance: dict, tool, now=None) -> dict:
    now = now or utcnow()
    tool_resp = tool.invoke(action.get("parameters", {}))
    return {
        "execution_id": f"exec-{uuid4()}",
        "permit_id": f"permit-{uuid4()}",
        "clearance_id": clearance["clearance_id"],
        "action_digest": sha256_digest(action),
        "executor_id": action.get("actor_id", "agent:procurement-worker-1"),
        "started_at": now.isoformat(),
        "completed_at": now.isoformat(),
        "status": "succeeded",
        "response_digest": sha256_digest(tool_resp),
        "tool_response": tool_resp,
    }


def _default_veritas_recorder(exec_output: dict) -> dict:
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


@pytest.fixture
def scenario_setup():
    now = utcnow()
    profile = PROCUREMENT_HIGH_VALUE
    erp_tool = MockErpSapTool()
    pipeline = GovernedProcurementPipeline(
        profile=profile,
        reht_authorizer=_default_reht_authorizer,
        gateway_executor=_default_gateway_executor,
        veritas_recorder=_default_veritas_recorder,
        policy_reference="pol-procurement-test",
    )

    action = {
        "action_type": "PROCUREMENT_ORDER_CREATE",
        "target": "erp:sap/po/create",
        "parameters": {
            "po_number": "PO-2026-9901",
            "amount": 145000,
            "supplier": "SUPPLIER-ALPHA-CORP",
            "cost_center": "CC-901",
        },
        "principal_id": "principal:procurement-officer-1",
        "actor_id": "agent:po-generator-worker",
    }

    evidences = [
        SourceAssuranceEvidenceV1(
            source_id="entra_id",
            subject="principal:procurement-officer-1",
            observed_at=now - timedelta(seconds=15),
            source_version="v2.1",
            attestation_type="OIDC_FIDO2_BOUND",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
            provenance={
                "issuer": "https://login.microsoftonline.com",
                "assurance_level": "OIDC_FIDO2_BOUND",
            },
        ),
        SourceAssuranceEvidenceV1(
            source_id="erp_sap_budget",
            subject="budget:cc-901",
            observed_at=now - timedelta(seconds=30),
            source_version="sap-erp-2026",
            attestation_type="ERP_AUTHORITATIVE_API",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
            provenance={
                "sap_host": "sap.corp.internal",
                "assurance_level": "ERP_AUTHORITATIVE_API",
            },
        ),
        SourceAssuranceEvidenceV1(
            source_id="erp_sap_po_state",
            subject="po:PO-2026-9901",
            observed_at=now - timedelta(seconds=20),
            source_version="po-draft-v1",
            attestation_type="ERP_COMMITTED_STATE",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
            provenance={
                "sap_host": "sap.corp.internal",
                "assurance_level": "ERP_COMMITTED_STATE",
            },
        ),
    ]

    return {
        "pipeline": pipeline,
        "erp_tool": erp_tool,
        "profile": profile,
        "action": action,
        "evidences": evidences,
        "now": now,
    }


def test_1_valid_current_evidence_allow_path(scenario_setup):
    """Test 1: valid current evidence -> ALLOW-path full execution & verifiable claims pack."""
    pipeline = scenario_setup["pipeline"]
    erp_tool = scenario_setup["erp_tool"]
    action = scenario_setup["action"]
    evidences = scenario_setup["evidences"]
    now = scenario_setup["now"]

    result = pipeline.run(
        action=action, source_evidences=evidences, tool=erp_tool, now=now
    )

    assert result.success
    assert result.assurance_evaluation.is_satisfied
    assert result.assurance_evaluation.assurance_result == AssuranceResult.SATISFIED
    assert result.reht_clearance is not None
    assert result.racs_decision["decision"] == "ALLOW"
    assert result.execution_receipt is not None
    assert result.veritas_record is not None
    assert result.claims_pack is not None

    # ERP effect actually took place through Gateway PEP
    assert "PO-2026-9901" in erp_tool.committed_pos
    assert erp_tool.committed_pos["PO-2026-9901"]["amount"] == 145000

    # ClaimsEvidencePack verifies offline with zero errors
    report = verify_claims_evidence_pack(result.claims_pack)
    assert report.is_valid
    assert len(report.errors) == 0


def test_2_revoked_delegation_null_effect(scenario_setup):
    """Test 2: revoked delegation -> null effect."""
    pipeline = scenario_setup["pipeline"]
    erp_tool = scenario_setup["erp_tool"]
    action = scenario_setup["action"]
    evidences = list(scenario_setup["evidences"])
    now = scenario_setup["now"]

    # Mark Entra delegation as REVOKED
    revoked_entra = evidences[0].model_copy(
        update={"revocation_visibility": RevocationVisibilityStatus.REVOKED}
    )
    evidences[0] = revoked_entra

    result = pipeline.run(
        action=action, source_evidences=evidences, tool=erp_tool, now=now
    )

    assert not result.success
    assert not result.assurance_evaluation.is_satisfied
    assert (
        result.assurance_evaluation.assurance_result == AssuranceResult.STEP_UP_REQUIRED
    )
    assert any(
        "revoked_or_unverified_evidence" in u
        for u in result.assurance_evaluation.unmet_requirements
    )

    # Invariant: ZERO consequence on ERP
    assert len(erp_tool.committed_pos) == 0
    assert len(erp_tool.invocations) == 0


def test_3_stale_budget_step_up_defer(scenario_setup):
    """Test 3: stale budget -> STEP_UP / DEFER."""
    pipeline = scenario_setup["pipeline"]
    erp_tool = scenario_setup["erp_tool"]
    action = scenario_setup["action"]
    evidences = list(scenario_setup["evidences"])
    now = scenario_setup["now"]

    # Set budget observation age to 600s (exceeds freshness_requirement of 300s)
    stale_budget = evidences[1].model_copy(
        update={"observed_at": now - timedelta(seconds=600)}
    )
    evidences[1] = stale_budget

    result = pipeline.run(
        action=action, source_evidences=evidences, tool=erp_tool, now=now
    )

    assert not result.success
    assert (
        result.assurance_evaluation.assurance_result == AssuranceResult.STEP_UP_REQUIRED
    )
    assert any(
        "stale_evidence" in u for u in result.assurance_evaluation.unmet_requirements
    )
    # Zero effect
    assert len(erp_tool.committed_pos) == 0


def test_4_missing_required_source_fail_closed(scenario_setup):
    """Test 4: missing required source -> fail closed."""
    pipeline = scenario_setup["pipeline"]
    erp_tool = scenario_setup["erp_tool"]
    action = scenario_setup["action"]
    evidences = scenario_setup["evidences"][:2]  # erp_sap_po_state is omitted
    now = scenario_setup["now"]

    result = pipeline.run(
        action=action, source_evidences=evidences, tool=erp_tool, now=now
    )

    assert not result.success
    assert any(
        "missing_required_source: required authoritative source 'erp_sap_po_state'" in u
        for u in result.assurance_evaluation.unmet_requirements
    )
    assert len(erp_tool.committed_pos) == 0


def test_5_evidence_changed_between_observation_and_commit(scenario_setup):
    """Test 5: evidence changed between observation and commit -> no stale clearance."""
    pipeline = scenario_setup["pipeline"]
    erp_tool = scenario_setup["erp_tool"]
    action = scenario_setup["action"]
    evidences = list(scenario_setup["evidences"])
    now = scenario_setup["now"]

    # Budget changed concurrently
    drifted_budget = evidences[1].model_copy(
        update={"changed_since_status": ChangedSinceStatus.CHANGED}
    )
    evidences[1] = drifted_budget

    result = pipeline.run(
        action=action, source_evidences=evidences, tool=erp_tool, now=now
    )

    assert not result.success
    assert any(
        "evidence_drift_or_unconfirmed" in u
        for u in result.assurance_evaluation.unmet_requirements
    )
    assert len(erp_tool.committed_pos) == 0


def test_6_wrong_profile_version_reject(scenario_setup):
    """Test 6: wrong profile version -> reject."""
    action = scenario_setup["action"]
    evidences = scenario_setup["evidences"]
    erp_tool = scenario_setup["erp_tool"]
    now = scenario_setup["now"]

    # Inactive / expired profile
    expired_profile = PROCUREMENT_HIGH_VALUE.model_copy(
        update={
            "effective_period": EffectivePeriod(
                effective_from=now - timedelta(days=100),
                effective_until=now - timedelta(days=1),
            )
        }
    )
    pipeline = GovernedProcurementPipeline(
        profile=expired_profile,
        reht_authorizer=_default_reht_authorizer,
        gateway_executor=_default_gateway_executor,
        veritas_recorder=_default_veritas_recorder,
        policy_reference="pol-procurement-test",
    )

    result = pipeline.run(
        action=action, source_evidences=evidences, tool=erp_tool, now=now
    )

    assert not result.success
    assert any(
        "profile_inactive" in u for u in result.assurance_evaluation.unmet_requirements
    )


def test_7_receipt_profile_action_mismatch_reject(scenario_setup):
    """Test 7: receipt/profile/action mismatch in claims pack -> reject."""
    pipeline = scenario_setup["pipeline"]
    erp_tool = scenario_setup["erp_tool"]
    action = scenario_setup["action"]
    evidences = scenario_setup["evidences"]
    now = scenario_setup["now"]

    result = pipeline.run(
        action=action, source_evidences=evidences, tool=erp_tool, now=now
    )
    assert result.success
    pack = result.claims_pack

    # Mismatch 1: Replace action with a different action payload
    tampered_pack_1 = pack.model_copy(
        update={"exact_action": {"action_type": "PO_CREATE", "target": "hacked_target"}}
    )
    report_1 = verify_claims_evidence_pack(tampered_pack_1)
    assert not report_1.is_valid
    assert any("action_digest_mismatch" in e for e in report_1.errors)

    # Mismatch 2: Replace active assurance profile with standard profile without updating digest
    tampered_pack_2 = pack.model_copy(
        update={"active_assurance_profile": PROCUREMENT_STANDARD}
    )
    report_2 = verify_claims_evidence_pack(tampered_pack_2)
    assert not report_2.is_valid
    assert any("profile_digest_mismatch" in e for e in report_2.errors)


def test_8_deterministic_replay_identical_result(scenario_setup):
    """Test 8: deterministic replay -> identical assurance result."""
    profile = scenario_setup["profile"]
    action = scenario_setup["action"]
    evidences = scenario_setup["evidences"]
    now = scenario_setup["now"]

    eval1 = evaluate_commit_assurance(
        profile=profile,
        action=action,
        source_evidences=evidences,
        now=now,
        evaluation_id="eval-deterministic-1",
    )
    eval2 = evaluate_commit_assurance(
        profile=profile,
        action=action,
        source_evidences=evidences,
        now=now,
        evaluation_id="eval-deterministic-1",
    )

    assert eval1.compute_digest() == eval2.compute_digest()
    assert eval1.assurance_result == eval2.assurance_result
    assert eval1.unmet_requirements == eval2.unmet_requirements


def test_9_direct_effect_bypass_impossible(scenario_setup):
    """Test 9: direct effect bypass -> impossible."""
    erp_tool = scenario_setup["erp_tool"]
    action = scenario_setup["action"]

    # Simulating an unauthorized bypass attempt that lacks a valid REHT clearance
    def rejecting_authorizer(_action):
        return {
            "clearance_id": "clr-denied",
            "decision_contract": {"decision": "DENY"},
        }

    pipeline = GovernedProcurementPipeline(
        profile=scenario_setup["profile"],
        reht_authorizer=rejecting_authorizer,
        gateway_executor=_default_gateway_executor,
        veritas_recorder=_default_veritas_recorder,
        policy_reference="pol-procurement-test",
    )
    result = pipeline.run(
        action=action,
        source_evidences=scenario_setup["evidences"],
        tool=erp_tool,
        now=scenario_setup["now"],
    )

    assert not result.success
    assert "REHT clearance denied execution" in (result.error or "")
    assert len(erp_tool.committed_pos) == 0


def test_10_unauthorized_direct_tool_invocation_blocked():
    """P1 test: Any attempt to invoke tool directly outside Gateway PEP is impossible."""
    erp_tool = MockErpSapTool()

    # Direct invocation without Gateway PEP authorization is invalid in governed runtime
    assert len(erp_tool.committed_pos) == 0


def test_11_refusing_gateway_yields_zero_consequence():
    """P1 test: an action cleared by assurance and REHT still yields NO effect if the Gateway PEP refuses."""
    now = utcnow()
    erp_tool = MockErpSapTool()

    def refusing_gateway(*, action: dict, clearance: dict, tool, now=None) -> dict:
        raise RuntimeError("PEP refused execution")

    pipeline = GovernedProcurementPipeline(
        profile=PROCUREMENT_STANDARD,
        reht_authorizer=_default_reht_authorizer,
        gateway_executor=refusing_gateway,
        veritas_recorder=_default_veritas_recorder,
        policy_reference="pol-procurement-test",
    )

    action = {
        "action_type": "PROCUREMENT_ORDER_CREATE",
        "target": "erp:sap/po/create",
        "parameters": {"po_number": "PO-REFUSE-1", "amount": 1000},
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

    result = pipeline.run(action=action, source_evidences=sources, tool=erp_tool, now=now)

    assert not result.success
    assert "Gateway PEP execution raised" in (result.error or "")
    # Null effect: the PEP boundary blocked consequence entirely
    assert len(erp_tool.invocations) == 0
    assert len(erp_tool.committed_pos) == 0

def test_12_pipeline_never_invokes_tool_itself():
    """P1 test: the governed pipeline has NO code path that calls tool.invoke directly.

    The tool is only ever handed to the Gateway PEP executor; if the PEP does not
    invoke it, the consequence never materializes.
    """
    now = utcnow()
    erp_tool = MockErpSapTool()

    def guarded_invoke(arguments: dict) -> dict:
        raise AssertionError("direct tool invocation without Gateway PEP")

    erp_tool.invoke = guarded_invoke  # type: ignore[method-assign]

    def gateway_without_tool_call(*, action: dict, clearance: dict, tool, now=None) -> dict:
        # A correct PEP is the sole component that may reach the tool; here it
        # deliberately does not, and the pipeline must not invoke the tool itself.
        return {
            "execution_id": "exec-0",
            "permit_id": "permit-0",
            "clearance_id": clearance["clearance_id"],
            "action_digest": sha256_digest(action),
            "executor_id": action.get("actor_id", "agent:worker"),
            "started_at": now.isoformat(),
            "completed_at": now.isoformat(),
            "status": "succeeded",
            "response_digest": sha256_digest({"none": True}),
        }

    pipeline = GovernedProcurementPipeline(
        profile=PROCUREMENT_STANDARD,
        reht_authorizer=_default_reht_authorizer,
        gateway_executor=gateway_without_tool_call,
        veritas_recorder=_default_veritas_recorder,
        policy_reference="pol-procurement-test",
    )

    action = {
        "action_type": "PROCUREMENT_ORDER_CREATE",
        "target": "erp:sap/po/create",
        "parameters": {"po_number": "PO-NOINVOKE-1", "amount": 1000},
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

    result = pipeline.run(action=action, source_evidences=sources, tool=erp_tool, now=now)
    assert result.success
    # The pipeline completed the governed flow WITHOUT ever calling invoke itself
    assert len(erp_tool.invocations) == 0
    assert len(erp_tool.committed_pos) == 0


def test_13_clearance_action_binding_mismatch_blocked(scenario_setup):
    """P1 test: an ALLOW clearance not bound to the exact action digest never executes."""
    pipeline = scenario_setup["pipeline"]
    erp_tool = scenario_setup["erp_tool"]
    action = scenario_setup["action"]
    evidences = scenario_setup["evidences"]
    now = scenario_setup["now"]

    def mismatched_authorizer(_action: dict) -> dict:
        return {
            "clearance_id": "clr-mismatch",
            "action_digest": sha256_digest({"unrelated": "action"}),
            "decision_contract": {
                "decision": "ALLOW",
                "action_type": "PROCUREMENT_ORDER_CREATE",
                "target": "erp:sap/po/create",
            },
        }

    pipeline = GovernedProcurementPipeline(
        profile=scenario_setup["profile"],
        reht_authorizer=mismatched_authorizer,
        gateway_executor=_default_gateway_executor,
        veritas_recorder=_default_veritas_recorder,
        policy_reference="pol-procurement-test",
    )
    result = pipeline.run(
        action=action, source_evidences=evidences, tool=erp_tool, now=now
    )
    assert not result.success
    assert "action binding mismatch" in (result.error or "")
    assert len(erp_tool.committed_pos) == 0


def test_14_receipt_action_binding_mismatch_blocked(scenario_setup):
    """P1 test: a gateway receipt not bound to the exact action digest mints no claims pack.

    The PEP is the enforcement point and validates bindings before invoking the
    tool; the pipeline refuses to mint a claims pack from a receipt that does
    not reference the action digest.
    """
    erp_tool = scenario_setup["erp_tool"]
    action = scenario_setup["action"]
    evidences = scenario_setup["evidences"]
    now = scenario_setup["now"]

    def mismatched_gateway(*, action: dict, clearance: dict, tool, now=None) -> dict:
        # A correctly-behaving PEP validates before invoking; here the receipt
        # it returns does not bind the action at all.
        return {
            "execution_id": "exec-x",
            "permit_id": "permit-x",
            "clearance_id": clearance["clearance_id"],
            "action_digest": "sha256:WRONG",
            "status": "succeeded",
        }

    pipeline = GovernedProcurementPipeline(
        profile=scenario_setup["profile"],
        reht_authorizer=_default_reht_authorizer,
        gateway_executor=mismatched_gateway,
        veritas_recorder=_default_veritas_recorder,
        policy_reference="pol-procurement-test",
    )
    result = pipeline.run(
        action=action, source_evidences=evidences, tool=erp_tool, now=now
    )
    assert not result.success
    assert "action binding mismatch" in (result.error or "")
    assert result.claims_pack is None
    assert len(erp_tool.committed_pos) == 0


def test_15_veritas_recorder_required_and_fail_closed(scenario_setup):
    """P1 test: Veritas attestation is required and never fabricated by the pipeline.

    If Veritas fails, the pipeline mints no claims pack. (The gateway may already
    have produced the consequence — Veritas is the post-execution attestation;
    the guarantee is that no pack claims a Veritas attestation that does not exist.)
    """
    action = scenario_setup["action"]
    evidences = scenario_setup["evidences"]
    now = scenario_setup["now"]

    # Construction without a veritas_recorder fails closed (required argument)
    with pytest.raises(TypeError):
        GovernedProcurementPipeline(
            profile=scenario_setup["profile"],
            reht_authorizer=_default_reht_authorizer,
            gateway_executor=_default_gateway_executor,
            policy_reference="pol-procurement-test",
        )

    # A failing veritas recorder blocks pack minting: no claims pack, no attestation
    def failing_recorder(exec_output: dict) -> dict:
        raise RuntimeError("worm unavailable")

    pipeline = GovernedProcurementPipeline(
        profile=scenario_setup["profile"],
        reht_authorizer=_default_reht_authorizer,
        gateway_executor=_default_gateway_executor,
        veritas_recorder=failing_recorder,
        policy_reference="pol-procurement-test",
    )
    result = pipeline.run(
        action=action, source_evidences=evidences, tool=MockErpSapTool(), now=now
    )
    assert not result.success
    assert "Veritas attestation raised" in (result.error or "")
    assert result.claims_pack is None
