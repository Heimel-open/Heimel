from __future__ import annotations

import hashlib
import json

from valo_reht import RealReht
from valo_reht.approver_authority import APPROVER_AUTHORITY_V1
from valo_reht.execution_requirements import (
    EAR_GATE_V1,
    EAR_GOVERNANCE_GATE_V1,
    EAR_V1,
)


def _ctx() -> dict:
    return {
        "actor": "system-1",
        "identity": "id-system-1",
        "time": {"now": "2026-08-17T17:00:00+00:00"},
        "sequence": 17,
        "execution_nonce": "nonce-17",
        "state_ref": "state-17",
        "authority_state": {
            "drift_detected": False,
            "attested_surface_hash": "surface-a",
            "current_surface_hash": "surface-a",
        },
        "causal": {"hop_depth": 0},
        "evidence": {
            "status": "VALID",
            "fresh": True,
            "evidence_ref": "evidence:17",
        },
        "reality_validation": {
            "status": "MATCH",
            "evidence_ref": "reality:17",
        },
        "gates": {},
        "gate_attestations": {},
        "purpose": {
            "purpose_id": "p1",
            "purpose_type": "enterprise-operation",
            "scope": ["target-1"],
            "basis": "business-process:case-17",
            "permitted_data": [],
            "permitted_actions": ["EXECUTE_ACTION"],
            "validity": {
                "valid_from": "2026-08-17T16:00:00+00:00",
                "valid_until": "2026-08-17T18:00:00+00:00",
            },
        },
        "authority": [
            {
                "authority_id": "auth-1",
                "principal": "system-1",
                "capability": "EXECUTE_ACTION",
                "scope": ["target-1"],
                "constraints": {"purpose_id": "p1"},
                "validity": {
                    "valid_from": "2026-01-01T00:00:00+00:00",
                    "valid_until": "2030-01-01T00:00:00+00:00",
                },
                "status": "ACTIVE",
            }
        ],
    }


def _contract(**extra) -> dict:
    contract = {
        "execution_authorization_profile": EAR_V1,
        "capability": "EXECUTE_ACTION",
        "target": "target-1",
        "action_type": "EXECUTE_ACTION",
        "purpose_id": "p1",
        "state_ref": "state-17",
        "side_effecting": True,
        "impact": "MEDIUM",
        "reversible": True,
        "required_approver_capability": "APPROVE_EXECUTION",
    }
    contract.update(extra)
    return contract


def _action_hash(contract: dict) -> str:
    canonical = json.dumps(
        contract,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _approver_authority(contract: dict) -> dict:
    return {
        "schema": APPROVER_AUTHORITY_V1,
        "approver_actor": "approver-1",
        "authority_ref": "authority:approve:1",
        "capability": contract["required_approver_capability"],
        "target_ref": contract["target"],
        "purpose_id": contract["purpose_id"],
        "action_contract_hash": _action_hash(contract),
        "verified": True,
        "source": "authority-verifier-1",
        "evidence_ref": "evidence:authority:approve:1",
        "observed_at": "2026-08-17T16:58:00+00:00",
        "valid_until": "2026-08-17T17:05:00+00:00",
    }


def _gate_attestation(contract: dict, **extra) -> dict:
    attestation = {
        "schema": EAR_GATE_V1,
        "gate_type": "human_approval",
        "gate_ref": "approval:17",
        "verified": True,
        "authority_granted": False,
        "subject_actor": "system-1",
        "action_contract_hash": _action_hash(contract),
        "execution_nonce": "nonce-17",
        "source": "gate-verifier-1",
        "evidence_ref": "evidence:approval:17",
        "observed_at": "2026-08-17T16:59:00+00:00",
        "valid_until": "2026-08-17T17:05:00+00:00",
        "approver_actors": ["approver-1"],
        "approval_capability": contract["required_approver_capability"],
        "approver_authorities": [_approver_authority(contract)],
        "trigger_ref": "trigger:human-impact-or-local-policy",
        "criteria_results": [
            {"criterion_ref": "criterion:completeness", "result": "YES"},
            {"criterion_ref": "criterion:plausibility", "result": "YES"},
        ],
        "decision": "APPROVE",
        "escalation_ref": "escalation:owner-on-refusal",
        "record_ref": "record:approval:17",
    }
    attestation.update(extra)
    return attestation


def _authorize(ctx: dict, contract: dict):
    return RealReht().authorize(ctx, contract)


def _profiled_case(**attestation_extra):
    contract = _contract(
        governance_gate_profile=EAR_GOVERNANCE_GATE_V1,
        required_gate_types=["human_approval"],
    )
    ctx = _ctx()
    ctx["gates"] = {"human_approval_ref": "approval:17"}
    ctx["gate_attestations"] = {
        "approval:17": _gate_attestation(contract, **attestation_extra)
    }
    return ctx, contract


def test_profile_can_require_human_gate_for_medium_reversible_action() -> None:
    contract = _contract(governance_gate_profile=EAR_GOVERNANCE_GATE_V1)
    result = _authorize(_ctx(), contract)
    assert result.decision == "DENY"
    assert "required_gate_types" in (result.reason or "")


def test_profile_allows_complete_affirmative_human_gate() -> None:
    ctx, contract = _profiled_case()
    assert _authorize(ctx, contract).decision == "ALLOW"


def test_profile_requires_explicit_trigger() -> None:
    ctx, contract = _profiled_case(trigger_ref="")
    result = _authorize(ctx, contract)
    assert result.decision == "DENY"
    assert "trigger_ref" in (result.reason or "")


def test_profile_requires_explicit_criteria_results() -> None:
    ctx, contract = _profiled_case(criteria_results=[])
    result = _authorize(ctx, contract)
    assert result.decision == "DENY"
    assert "criteria results" in (result.reason or "")


def test_profile_no_result_cannot_satisfy_gate() -> None:
    ctx, contract = _profiled_case(
        criteria_results=[{"criterion_ref": "criterion:red-line", "result": "NO"}]
    )
    result = _authorize(ctx, contract)
    assert result.decision == "DENY"
    assert "not fully affirmative" in (result.reason or "")


def test_profile_partly_result_cannot_satisfy_gate() -> None:
    ctx, contract = _profiled_case(
        criteria_results=[{"criterion_ref": "criterion:red-line", "result": "PARTLY"}]
    )
    result = _authorize(ctx, contract)
    assert result.decision == "DENY"
    assert "not fully affirmative" in (result.reason or "")


def test_profile_refusal_cannot_satisfy_gate() -> None:
    ctx, contract = _profiled_case(decision="REFUSE")
    result = _authorize(ctx, contract)
    assert result.decision == "DENY"
    assert "positive decision" in (result.reason or "")


def test_profile_requires_escalation_route() -> None:
    ctx, contract = _profiled_case(escalation_ref="")
    result = _authorize(ctx, contract)
    assert result.decision == "DENY"
    assert "escalation_ref" in (result.reason or "")


def test_profile_requires_auditable_record() -> None:
    ctx, contract = _profiled_case(record_ref="")
    result = _authorize(ctx, contract)
    assert result.decision == "DENY"
    assert "record_ref" in (result.reason or "")


def test_unprofiled_existing_gate_semantics_remain_compatible() -> None:
    contract = _contract(
        impact="HIGH",
        required_gate_types=["human_approval"],
    )
    ctx = _ctx()
    ctx["gates"] = {"human_approval_ref": "approval:17"}
    attestation = _gate_attestation(contract)
    for field in (
        "trigger_ref",
        "criteria_results",
        "decision",
        "escalation_ref",
        "record_ref",
    ):
        del attestation[field]
    ctx["gate_attestations"] = {"approval:17": attestation}
    assert _authorize(ctx, contract).decision == "ALLOW"
