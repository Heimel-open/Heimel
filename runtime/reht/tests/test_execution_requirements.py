from __future__ import annotations

import hashlib
import json
from copy import deepcopy

from valo_reht import RealReht
from valo_reht.approver_authority import APPROVER_AUTHORITY_V1
from valo_reht.execution_requirements import EAR_GATE_V1, EAR_V1


def _ctx() -> dict:
    return {
        "actor": "system-1",
        "identity": "id-system-1",
        "time": {"now": "2026-08-10T09:00:00+00:00"},
        "sequence": 7,
        "execution_nonce": "nonce-7",
        "state_ref": "state-7",
        "authority_state": {
            "drift_detected": False,
            "attested_surface_hash": "surface-a",
            "current_surface_hash": "surface-a",
        },
        "causal": {"hop_depth": 0},
        "evidence": {"status": "VALID", "fresh": True, "evidence_ref": "evidence:7"},
        "reality_validation": {"status": "MATCH", "evidence_ref": "reality:7"},
        "gates": {},
        "gate_attestations": {},
        "purpose": {
            "purpose_id": "p1",
            "purpose_type": "enterprise-operation",
            "scope": ["target-1"],
            "basis": "business-process:case-7",
            "permitted_data": [],
            "permitted_actions": ["EXECUTE_ACTION"],
            "validity": {
                "valid_from": "2026-08-10T08:00:00+00:00",
                "valid_until": "2026-08-10T10:00:00+00:00",
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
        "state_ref": "state-7",
        "side_effecting": True,
        "impact": "MEDIUM",
        "reversible": True,
        "required_approver_capability": "APPROVE_EXECUTION",
    }
    contract.update(extra)
    return contract


def _action_hash(contract: dict) -> str:
    canonical = json.dumps(contract, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _approver_authority(
    contract: dict,
    *,
    actor: str,
    authority_ref: str,
) -> dict:
    return {
        "schema": APPROVER_AUTHORITY_V1,
        "approver_actor": actor,
        "authority_ref": authority_ref,
        "capability": contract["required_approver_capability"],
        "target_ref": contract["target"],
        "purpose_id": contract["purpose_id"],
        "action_contract_hash": _action_hash(contract),
        "verified": True,
        "source": "authority-verifier-1",
        "evidence_ref": f"evidence:{authority_ref}",
        "observed_at": "2026-08-10T08:58:00+00:00",
        "valid_until": "2026-08-10T09:05:00+00:00",
    }


def _gate_attestation(
    contract: dict,
    *,
    gate_type: str,
    gate_ref: str,
    approver_actors: list[str] | None = None,
    **extra,
) -> dict:
    attestation = {
        "schema": EAR_GATE_V1,
        "gate_type": gate_type,
        "gate_ref": gate_ref,
        "verified": True,
        "authority_granted": False,
        "subject_actor": "system-1",
        "action_contract_hash": _action_hash(contract),
        "execution_nonce": "nonce-7",
        "source": "gate-verifier-1",
        "evidence_ref": f"evidence:{gate_ref}",
        "observed_at": "2026-08-10T08:59:00+00:00",
        "valid_until": "2026-08-10T09:05:00+00:00",
    }
    if approver_actors is not None:
        attestation["approver_actors"] = approver_actors
    if gate_type in {"human_approval", "dual_control"} and approver_actors:
        attestation["approval_capability"] = contract["required_approver_capability"]
        attestation["approver_authorities"] = [
            _approver_authority(
                contract,
                actor=actor,
                authority_ref=f"authority:approve:{index + 1}",
            )
            for index, actor in enumerate(approver_actors)
        ]
    attestation.update(extra)
    return attestation


def _authorize(ctx: dict | None = None, contract: dict | None = None):
    return RealReht().authorize(ctx or _ctx(), contract or _contract())


def test_ear_v1_allows_compliant_action() -> None:
    assert _authorize().decision == "ALLOW"


def test_ea03_medium_side_effect_can_remain_unbound_by_default() -> None:
    ctx = _ctx()
    ctx["purpose"] = None
    ctx["authority"][0]["constraints"] = {}
    contract = _contract()
    del contract["purpose_id"]
    assert _authorize(ctx, contract).decision == "ALLOW"


def test_ea03_explicit_purpose_requirement_applies_to_medium_action() -> None:
    ctx = _ctx()
    ctx["purpose"] = None
    ctx["authority"][0]["constraints"] = {}
    contract = _contract(requires_purpose=True)
    del contract["purpose_id"]
    result = _authorize(ctx, contract)
    assert result.decision == "DENY"
    assert (result.reason or "").startswith("EA-03")


def test_ea03_high_impact_action_requires_purpose_id() -> None:
    contract = _contract(impact="HIGH")
    del contract["purpose_id"]
    result = _authorize(contract=contract)
    assert result.decision == "DENY"
    assert (result.reason or "").startswith("EA-03")


def test_ea03_high_impact_requires_registered_purpose() -> None:
    ctx = _ctx()
    ctx["purpose"] = None
    result = _authorize(ctx, _contract(impact="HIGH"))
    assert result.decision == "DENY"
    assert "registered purpose" in (result.reason or "")


def test_ea03_registered_purpose_must_match_action_purpose() -> None:
    ctx = _ctx()
    ctx["purpose"] = {**ctx["purpose"], "purpose_id": "p2"}
    result = _authorize(ctx, _contract(impact="HIGH"))
    assert result.decision == "DENY"
    assert "exact registered purpose" in (result.reason or "")


def test_ea03_registered_purpose_must_cover_target() -> None:
    ctx = _ctx()
    ctx["purpose"] = {**ctx["purpose"], "scope": ["other-target"]}
    result = _authorize(ctx, _contract(impact="HIGH"))
    assert result.decision == "DENY"
    assert "purpose scope" in (result.reason or "")


def test_ea03_registered_purpose_must_permit_action_type() -> None:
    ctx = _ctx()
    ctx["purpose"] = {**ctx["purpose"], "permitted_actions": ["READ_ONLY"]}
    result = _authorize(ctx, _contract(impact="HIGH"))
    assert result.decision == "DENY"
    assert "permit this action type" in (result.reason or "")


def test_ea03_expired_purpose_fails_closed() -> None:
    ctx = _ctx()
    ctx["purpose"] = {
        **ctx["purpose"],
        "validity": {
            "valid_from": "2026-08-10T07:00:00+00:00",
            "valid_until": "2026-08-10T08:59:59+00:00",
        },
    }
    result = _authorize(ctx, _contract(impact="HIGH"))
    assert result.decision == "DENY"
    assert "not active" in (result.reason or "")


def test_ea03_valid_identity_and_authority_cannot_bypass_exact_purpose_binding() -> None:
    ctx = _ctx()
    ctx["authority"][0]["constraints"] = {}
    ctx["gates"] = {"human_approval_ref": "approval:1"}
    result = _authorize(ctx, _contract(impact="HIGH"))
    assert result.decision == "DENY"
    assert "authority is not explicitly bound" in (result.reason or "")


def test_ea04_denies_broken_causal_state() -> None:
    ctx = _ctx()
    ctx["state_ref"] = "state-8"
    result = _authorize(ctx)
    assert result.decision == "DENY"
    assert (result.reason or "").startswith("EA-04")


def test_ea05_denies_explicit_authority_drift() -> None:
    ctx = _ctx()
    ctx["authority_state"]["drift_detected"] = True
    result = _authorize(ctx)
    assert result.decision == "DENY"
    assert (result.reason or "").startswith("EA-05")


def test_ea05_denies_authority_surface_mismatch() -> None:
    ctx = _ctx()
    ctx["authority_state"]["current_surface_hash"] = "surface-b"
    result = _authorize(ctx)
    assert result.decision == "DENY"
    assert (result.reason or "").startswith("EA-05")


def test_ea06_denies_transitive_multi_hop_authority() -> None:
    ctx = _ctx()
    ctx["causal"] = {"hop_depth": 1, "prior_permit_ref": "permit:prior", "reauthorized": False}
    result = _authorize(ctx)
    assert result.decision == "DENY"
    assert (result.reason or "").startswith("EA-06")


def test_ea06_allows_independently_reauthorized_hop() -> None:
    ctx = _ctx()
    ctx["causal"] = {"hop_depth": 1, "prior_permit_ref": "permit:prior", "reauthorized": True}
    assert _authorize(ctx).decision == "ALLOW"


def test_ea07_denies_unbounded_temporary_authority() -> None:
    ctx = _ctx()
    authority = deepcopy(ctx["authority"][0])
    authority["temporary"] = True
    authority["validity"] = {"valid_from": "2026-01-01T00:00:00+00:00"}
    ctx["authority"] = [authority]
    result = _authorize(ctx)
    assert result.decision == "DENY"
    assert (result.reason or "").startswith("EA-07")


def test_ea07_denies_wildcard_temporary_scope() -> None:
    ctx = _ctx()
    authority = deepcopy(ctx["authority"][0])
    authority["temporary"] = True
    authority["scope"] = ["*"]
    ctx["authority"] = [authority]
    result = _authorize(ctx)
    assert result.decision == "DENY"
    assert (result.reason or "").startswith("EA-07")


def test_ea08_denies_missing_required_evidence() -> None:
    ctx = _ctx()
    ctx["evidence"] = {"status": "VALID", "fresh": False, "evidence_ref": "evidence:7"}
    result = _authorize(ctx, _contract(requires_evidence=True))
    assert result.decision == "DENY"
    assert (result.reason or "").startswith("EA-08")


def test_ea08_allows_valid_required_evidence() -> None:
    assert _authorize(contract=_contract(requires_evidence=True)).decision == "ALLOW"


def test_ea09_denies_unverified_reality() -> None:
    ctx = _ctx()
    ctx["reality_validation"] = {"status": "DIVERGED", "evidence_ref": "reality:7"}
    result = _authorize(ctx, _contract(requires_reality_validation=True))
    assert result.decision == "DENY"
    assert (result.reason or "").startswith("EA-09")


def test_ea10_denies_unclassified_side_effect() -> None:
    contract = _contract()
    del contract["impact"]
    result = _authorize(contract=contract)
    assert result.decision == "DENY"
    assert (result.reason or "").startswith("EA-10")


def test_ea11_denies_high_impact_without_explicit_gate_policy() -> None:
    result = _authorize(contract=_contract(impact="HIGH"))
    assert result.decision == "DENY"
    assert "required_gate_types" in (result.reason or "")


def test_ea11_truthy_gate_ref_without_attestation_fails_closed() -> None:
    ctx = _ctx()
    ctx["gates"] = {"human_approval_ref": "approval:1"}
    contract = _contract(impact="HIGH", required_gate_types=["human_approval"])
    result = _authorize(ctx, contract)
    assert result.decision == "DENY"
    assert "typed attestation" in (result.reason or "")


def test_ea11_allows_high_impact_with_verified_action_bound_human_gate() -> None:
    ctx = _ctx()
    contract = _contract(impact="HIGH", required_gate_types=["human_approval"])
    ctx["gates"] = {"human_approval_ref": "approval:1"}
    ctx["gate_attestations"] = {
        "approval:1": _gate_attestation(
            contract,
            gate_type="human_approval",
            gate_ref="approval:1",
            approver_actors=["approver-1"],
        )
    }
    assert _authorize(ctx, contract).decision == "ALLOW"


def test_ea11_gate_attestation_must_bind_exact_action_contract() -> None:
    ctx = _ctx()
    contract = _contract(impact="HIGH", required_gate_types=["human_approval"])
    ctx["gates"] = {"human_approval_ref": "approval:1"}
    ctx["gate_attestations"] = {
        "approval:1": _gate_attestation(
            contract,
            gate_type="human_approval",
            gate_ref="approval:1",
            approver_actors=["approver-1"],
            action_contract_hash="0" * 64,
        )
    }
    result = _authorize(ctx, contract)
    assert result.decision == "DENY"
    assert "exact action contract" in (result.reason or "")


def test_ea11_gate_attestation_must_bind_current_execution_nonce() -> None:
    ctx = _ctx()
    contract = _contract(impact="HIGH", required_gate_types=["human_approval"])
    ctx["gates"] = {"human_approval_ref": "approval:1"}
    ctx["gate_attestations"] = {
        "approval:1": _gate_attestation(
            contract,
            gate_type="human_approval",
            gate_ref="approval:1",
            approver_actors=["approver-1"],
            execution_nonce="nonce-old",
        )
    }
    result = _authorize(ctx, contract)
    assert result.decision == "DENY"
    assert "current execution nonce" in (result.reason or "")


def test_ea11_gate_from_prior_execution_attempt_cannot_be_reused() -> None:
    ctx = _ctx()
    contract = _contract(impact="HIGH", required_gate_types=["human_approval"])
    ctx["gates"] = {"human_approval_ref": "approval:1"}
    ctx["gate_attestations"] = {
        "approval:1": _gate_attestation(
            contract,
            gate_type="human_approval",
            gate_ref="approval:1",
            approver_actors=["approver-1"],
        )
    }
    ctx["execution_nonce"] = "nonce-8"
    result = _authorize(ctx, contract)
    assert result.decision == "DENY"
    assert "current execution nonce" in (result.reason or "")


def test_ea11_human_approval_cannot_be_self_approval() -> None:
    ctx = _ctx()
    contract = _contract(impact="HIGH", required_gate_types=["human_approval"])
    ctx["gates"] = {"human_approval_ref": "approval:1"}
    ctx["gate_attestations"] = {
        "approval:1": _gate_attestation(
            contract,
            gate_type="human_approval",
            gate_ref="approval:1",
            approver_actors=["system-1"],
        )
    }
    result = _authorize(ctx, contract)
    assert result.decision == "DENY"
    assert "independent" in (result.reason or "")


def test_ea11_dual_control_requires_two_distinct_independent_approvers() -> None:
    ctx = _ctx()
    contract = _contract(impact="CRITICAL", required_gate_types=["dual_control"])
    ctx["gates"] = {"dual_control_ref": "dual:1"}
    ctx["gate_attestations"] = {
        "dual:1": _gate_attestation(
            contract,
            gate_type="dual_control",
            gate_ref="dual:1",
            approver_actors=["approver-1"],
        )
    }
    result = _authorize(ctx, contract)
    assert result.decision == "DENY"
    assert "at least two" in (result.reason or "")


def test_ea11_all_declared_gates_are_required() -> None:
    ctx = _ctx()
    contract = _contract(
        impact="CRITICAL",
        required_gate_types=["human_approval", "step_up"],
    )
    ctx["gates"] = {"human_approval_ref": "approval:1"}
    ctx["gate_attestations"] = {
        "approval:1": _gate_attestation(
            contract,
            gate_type="human_approval",
            gate_ref="approval:1",
            approver_actors=["approver-1"],
        )
    }
    result = _authorize(ctx, contract)
    assert result.decision == "DENY"
    assert "step_up" in (result.reason or "")


def test_ea11_gate_attestation_cannot_smuggle_authority() -> None:
    ctx = _ctx()
    contract = _contract(impact="HIGH", required_gate_types=["human_approval"])
    ctx["gates"] = {"human_approval_ref": "approval:1"}
    ctx["gate_attestations"] = {
        "approval:1": _gate_attestation(
            contract,
            gate_type="human_approval",
            gate_ref="approval:1",
            approver_actors=["approver-1"],
            authority_granted=True,
        )
    }
    result = _authorize(ctx, contract)
    assert result.decision == "DENY"
    assert "carry authority" in (result.reason or "")


def test_ea11_irreversible_action_also_requires_explicit_gate_policy() -> None:
    result = _authorize(contract=_contract(reversible=False))
    assert result.decision == "DENY"
    assert "required_gate_types" in (result.reason or "")


def test_ea14_denies_missing_sequence() -> None:
    ctx = _ctx()
    del ctx["sequence"]
    result = _authorize(ctx)
    assert result.decision == "DENY"
    assert (result.reason or "").startswith("EA-14")


def test_ea14_denies_missing_nonce() -> None:
    ctx = _ctx()
    del ctx["execution_nonce"]
    result = _authorize(ctx)
    assert result.decision == "DENY"
    assert (result.reason or "").startswith("EA-14")


def test_ea14_nonce_is_bound_into_permit() -> None:
    first = _ctx()
    second = _ctx()
    second["execution_nonce"] = "nonce-8"
    result_a = _authorize(first)
    result_b = _authorize(second)
    assert result_a.decision == result_b.decision == "ALLOW"
    assert result_a.permit_ref != result_b.permit_ref


def test_ea18_denies_missing_required_resource_bounds() -> None:
    result = _authorize(contract=_contract(resource_limits_required=True))
    assert result.decision == "DENY"
    assert (result.reason or "").startswith("EA-18")


def test_ea18_allows_declared_resource_bounds() -> None:
    contract = _contract(resource_limits_required=True, resource_limits={"max_external_calls": 2})
    assert _authorize(contract=contract).decision == "ALLOW"


def test_legacy_contract_remains_compatible() -> None:
    legacy = {
        "capability": "EXECUTE_ACTION",
        "target": "target-1",
        "action_type": "EXECUTE_ACTION",
    }
    ctx = _ctx()
    del ctx["sequence"]
    del ctx["execution_nonce"]
    assert _authorize(ctx, legacy).decision == "ALLOW"
