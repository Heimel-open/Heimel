from __future__ import annotations

from copy import deepcopy

import pytest

from valo_reht import RealReht
from valo_reht.confidential_execution import substrate_binding_digest
from valo_reht.execution_requirements import EAR_V1


def _substrate() -> dict:
    evidence = {
        "schema_version": "confidential_execution_binding.v1",
        "substrate_kind": "TEE",
        "attested_workspace_digest": "sha256:" + "a" * 64,
        "substrate_attestation_digest": "sha256:" + "b" * 64,
        "attestation_evidence_digest": "sha256:" + "c" * 64,
        "evidence_ref": "attestation:tee-1",
        "substrate_id": "gpu-node-1",
        "tee_type": "NVIDIA_CC",
        "gpu_identity": "gpu:0000:01:00.0",
        "cc_mode": "CONFIDENTIAL_COMPUTE",
        "measurement": "sha384:trusted-measurement",
        "attestation_verifier": "verifier:enterprise-tee",
        "attested_at": "2026-08-10T08:59:00+00:00",
        "valid_until": "2026-08-10T09:10:00+00:00",
        "max_attestation_age_seconds": 300,
        "model_digest": "sha256:" + "d" * 64,
        "workload_digest": "sha256:" + "e" * 64,
        "verification_status": "VERIFIED",
        "revoked": False,
        "confidentiality_protected": True,
        "integrity_protected": True,
        "isolation_enforced": True,
        "authority_effect": "NO_AUTHORITY_CREATION",
        "can_issue_clearance": False,
    }
    evidence["binding_digest"] = substrate_binding_digest(evidence)
    return evidence


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
        "execution_substrate": _substrate(),
        "authority": [
            {
                "authority_id": "auth-1",
                "principal": "system-1",
                "capability": "EXECUTE_ACTION",
                "scope": ["target-1"],
                "constraints": {},
                "validity": {
                    "valid_from": "2026-01-01T00:00:00+00:00",
                    "valid_until": "2030-01-01T00:00:00+00:00",
                },
                "status": "ACTIVE",
            }
        ],
    }


def _contract(ctx: dict | None = None, **updates) -> dict:
    ctx = ctx or _ctx()
    substrate = ctx["execution_substrate"]
    contract = {
        "execution_authorization_profile": EAR_V1,
        "capability": "EXECUTE_ACTION",
        "target": "target-1",
        "action_type": "EXECUTE_ACTION",
        "state_ref": "state-7",
        "side_effecting": True,
        "impact": "MEDIUM",
        "reversible": True,
        "requires_confidential_execution": True,
        "execution_substrate_binding_digest": substrate["binding_digest"],
        "execution_substrate_evidence_ref": substrate["evidence_ref"],
        "execution_model_digest": substrate["model_digest"],
        "execution_workload_digest": substrate["workload_digest"],
        "execution_measurement": substrate["measurement"],
    }
    contract.update(updates)
    return contract


def _authorize(ctx: dict, contract: dict):
    return RealReht().authorize(ctx, contract)


def _reseal(ctx: dict) -> None:
    substrate = ctx["execution_substrate"]
    substrate["binding_digest"] = substrate_binding_digest(substrate)


def test_exact_verified_fresh_tee_continuity_allows() -> None:
    ctx = _ctx()
    result = _authorize(ctx, _contract(ctx))
    assert result.decision == "ALLOW"
    assert result.clearance_ref is not None
    assert result.permit_ref is not None


def test_non_confidential_ear_action_preserves_existing_behavior() -> None:
    ctx = _ctx()
    ctx.pop("execution_substrate")
    contract = {
        "execution_authorization_profile": EAR_V1,
        "capability": "EXECUTE_ACTION",
        "target": "target-1",
        "action_type": "EXECUTE_ACTION",
        "state_ref": "state-7",
        "side_effecting": True,
        "impact": "MEDIUM",
        "reversible": True,
    }
    assert _authorize(ctx, contract).decision == "ALLOW"


def test_required_tee_missing_fails_closed() -> None:
    ctx = _ctx()
    contract = _contract(ctx)
    ctx.pop("execution_substrate")
    result = _authorize(ctx, contract)
    assert result.decision == "DENY"
    assert "EA-19" in (result.reason or "")
    assert "absent" in (result.reason or "")


def test_evaluated_substrate_digest_mismatch_fails_closed() -> None:
    ctx = _ctx()
    contract = _contract(ctx)
    contract["execution_substrate_binding_digest"] = "sha256:" + "0" * 64
    result = _authorize(ctx, contract)
    assert result.decision == "DENY"
    assert "differs from the evaluated action" in (result.reason or "")


def test_tampered_substrate_payload_fails_even_when_claimed_digest_is_unchanged() -> None:
    ctx = _ctx()
    contract = _contract(ctx)
    ctx["execution_substrate"]["gpu_identity"] = "gpu:tampered"
    result = _authorize(ctx, contract)
    assert result.decision == "DENY"
    assert "internally inconsistent" in (result.reason or "")


@pytest.mark.parametrize("status", ["INVALID", "REVOKED", "UNKNOWN"])
def test_unverified_substrate_status_fails_closed(status: str) -> None:
    ctx = _ctx()
    ctx["execution_substrate"]["verification_status"] = status
    _reseal(ctx)
    contract = _contract(ctx)
    result = _authorize(ctx, contract)
    assert result.decision == "DENY"
    assert "not verified" in (result.reason or "")


def test_revoked_substrate_fails_closed() -> None:
    ctx = _ctx()
    ctx["execution_substrate"]["revoked"] = True
    _reseal(ctx)
    result = _authorize(ctx, _contract(ctx))
    assert result.decision == "DENY"
    assert "revoked" in (result.reason or "")


def test_stale_substrate_fails_closed() -> None:
    ctx = _ctx()
    ctx["time"]["now"] = "2026-08-10T09:05:01+00:00"
    result = _authorize(ctx, _contract(ctx))
    assert result.decision == "DENY"
    assert "stale" in (result.reason or "")


def test_expired_substrate_fails_closed() -> None:
    ctx = _ctx()
    ctx["time"]["now"] = "2026-08-10T09:10:00+00:00"
    result = _authorize(ctx, _contract(ctx))
    assert result.decision == "DENY"
    assert "expired" in (result.reason or "")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("confidentiality_protected", False, "confidentiality"),
        ("integrity_protected", False, "integrity"),
        ("isolation_enforced", False, "isolation"),
        ("authority_effect", "GRANTS_AUTHORITY", "create authority"),
        ("can_issue_clearance", True, "issue clearance"),
    ],
)
def test_substrate_cannot_bypass_required_protection_or_authority_boundary(
    field: str,
    value,
    message: str,
) -> None:
    ctx = _ctx()
    ctx["execution_substrate"][field] = value
    _reseal(ctx)
    result = _authorize(ctx, _contract(ctx))
    assert result.decision == "DENY"
    assert message in (result.reason or "")


@pytest.mark.parametrize(
    ("contract_field", "value", "message"),
    [
        ("execution_model_digest", "sha256:" + "0" * 64, "model"),
        ("execution_workload_digest", "sha256:" + "0" * 64, "workload"),
        ("execution_measurement", "sha384:other", "measurement"),
        ("execution_substrate_evidence_ref", "attestation:other", "evidence reference"),
    ],
)
def test_exact_material_substrate_binding_is_rechecked(
    contract_field: str,
    value: str,
    message: str,
) -> None:
    ctx = _ctx()
    result = _authorize(ctx, _contract(ctx, **{contract_field: value}))
    assert result.decision == "DENY"
    assert message in (result.reason or "")


def test_clearance_and_permit_are_deterministic_and_bind_substrate() -> None:
    ctx = _ctx()
    contract = _contract(ctx)
    first = _authorize(deepcopy(ctx), deepcopy(contract))
    second = _authorize(deepcopy(ctx), deepcopy(contract))
    assert first.decision == second.decision == "ALLOW"
    assert first.clearance_ref == second.clearance_ref
    assert first.permit_ref == second.permit_ref

    changed_ctx = deepcopy(ctx)
    changed_ctx["execution_substrate"]["measurement"] = "sha384:new-measurement"
    _reseal(changed_ctx)
    changed_contract = _contract(changed_ctx)
    changed = _authorize(changed_ctx, changed_contract)
    assert changed.decision == "ALLOW"
    assert changed.clearance_ref != first.clearance_ref
    assert changed.permit_ref != first.permit_ref
