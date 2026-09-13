from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta

import pytest
from aas import (
    GateAttestationAdapter,
    GateAttestationInputError,
    TrustedSigningKeyV1,
    build_reht_gate_context,
)

from valo_reht import EAR_V1, RealReht

NOW = datetime.fromisoformat("2026-08-11T16:00:00+00:00")
SIGNING_KEY = b"approval-service-test-key"
SOURCE_ID = "approval-service-1"
SIGNING_KEY_ID = "approval-key-1"
EXECUTION_NONCE = "nonce-7"


def _contract(**extra) -> dict:
    contract = {
        "execution_authorization_profile": EAR_V1,
        "capability": "EXECUTE_ACTION",
        "target": "target-1",
        "action_type": "EXECUTE_ACTION",
        "purpose_id": "p1",
        "state_ref": "state-7",
        "side_effecting": True,
        "impact": "HIGH",
        "reversible": True,
        "required_gate_types": ["human_approval"],
        "required_approver_capability": "APPROVE_EXECUTION",
    }
    contract.update(extra)
    return contract


def _action_hash(contract: dict) -> str:
    canonical = json.dumps(contract, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _record(
    contract: dict,
    *,
    signing_key: bytes = SIGNING_KEY,
    signing_key_id: str = SIGNING_KEY_ID,
    execution_nonce: str = EXECUTION_NONCE,
    include_approver_authority: bool = True,
):
    raw = {
        "version": 1,
        "source_id": SOURCE_ID,
        "source_class": "EXTERNAL",
        "signing_key_id": signing_key_id,
        "subject_actor": "system-1",
        "gate_type": "human_approval",
        "gate_ref": "approval:1",
        "action_contract_hash": _action_hash(contract),
        "execution_nonce": execution_nonce,
        "observed_at": "2026-08-11T15:59:00+00:00",
        "valid_until": "2026-08-11T16:05:00+00:00",
        "evidence_refs": ["evidence:approval:1"],
        "verification_method": "ed25519",
        "verified": True,
        "approver_actors": ["approver-1"],
    }
    if include_approver_authority:
        raw["approval_capability"] = contract["required_approver_capability"]
        raw["approver_authorities"] = [
            {
                "version": 1,
                "approver_actor": "approver-1",
                "authority_ref": "authority:approve:1",
                "capability": contract["required_approver_capability"],
                "target_ref": contract["target"],
                "purpose_id": contract["purpose_id"],
                "action_contract_hash": _action_hash(contract),
                "verified": True,
                "source": "authority-verifier-1",
                "evidence_ref": "evidence:authority:approve:1",
                "observed_at": "2026-08-11T15:58:00+00:00",
                "valid_until": "2026-08-11T16:05:00+00:00",
            }
        ]
    return GateAttestationAdapter().attest(
        raw,
        now=NOW,
        tenant_id="tenant-1",
        signing_key=signing_key,
    )[1]


def _trusted_key(
    *,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
    revoked_at: datetime | None = None,
    revocation_ref: str | None = None,
) -> TrustedSigningKeyV1:
    return TrustedSigningKeyV1(
        source_id=SOURCE_ID,
        key_id=SIGNING_KEY_ID,
        signing_key=SIGNING_KEY,
        valid_from=valid_from or NOW - timedelta(hours=1),
        valid_until=valid_until or NOW + timedelta(hours=1),
        revoked_at=revoked_at,
        revocation_ref=revocation_ref,
    )


def _registry(key: TrustedSigningKeyV1 | None = None):
    return {(SOURCE_ID, SIGNING_KEY_ID): key or _trusted_key()}


def _ctx(fragment: dict | None = None, *, execution_nonce: str = EXECUTION_NONCE) -> dict:
    fragment = fragment or {"gates": {}, "gate_attestations": {}}
    return {
        "actor": "system-1",
        "identity": "id-system-1",
        "time": {"now": NOW.isoformat()},
        "sequence": 7,
        "execution_nonce": execution_nonce,
        "state_ref": "state-7",
        "authority_state": {
            "drift_detected": False,
            "attested_surface_hash": "surface-a",
            "current_surface_hash": "surface-a",
        },
        "causal": {"hop_depth": 0},
        "purpose": {
            "purpose_id": "p1",
            "purpose_type": "enterprise-operation",
            "scope": ["target-1"],
            "basis": "business-process:case-7",
            "permitted_data": [],
            "permitted_actions": ["EXECUTE_ACTION"],
            "validity": {
                "valid_from": "2026-08-11T15:00:00+00:00",
                "valid_until": "2026-08-11T17:00:00+00:00",
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
        **fragment,
    }


def test_signed_trusted_aas_gate_satisfies_reht_high_impact_contract() -> None:
    contract = _contract()
    record = _record(contract)
    fragment = build_reht_gate_context(
        [record],
        trusted_signing_keys=_registry(),
        now=NOW,
    )
    result = RealReht().authorize(_ctx(fragment), contract)
    assert result.decision == "ALLOW"
    assert result.permit_ref


def test_signed_gate_without_approver_authority_remains_denied() -> None:
    contract = _contract()
    record = _record(contract, include_approver_authority=False)
    fragment = build_reht_gate_context(
        [record],
        trusted_signing_keys=_registry(),
        now=NOW,
    )
    result = RealReht().authorize(_ctx(fragment), contract)
    assert result.decision == "DENY"
    assert (result.reason or "").startswith("EA-11")
    assert "approval capability" in (result.reason or "")


def test_missing_aas_gate_evidence_keeps_high_impact_execution_denied() -> None:
    result = RealReht().authorize(_ctx(), _contract())
    assert result.decision == "DENY"
    assert (result.reason or "").startswith("EA-11")


def test_spoofed_trusted_source_never_reaches_reht_gate_context() -> None:
    contract = _contract()
    spoofed = _record(contract, signing_key=b"attacker-key")
    with pytest.raises(GateAttestationInputError, match="verification failed"):
        build_reht_gate_context(
            [spoofed],
            trusted_signing_keys=_registry(),
            now=NOW,
        )


def test_unknown_signing_key_id_never_reaches_reht_gate_context() -> None:
    contract = _contract()
    old_key_record = _record(contract, signing_key_id="old-key")
    with pytest.raises(GateAttestationInputError, match="not in the trusted"):
        build_reht_gate_context(
            [old_key_record],
            trusted_signing_keys=_registry(),
            now=NOW,
        )


def test_expired_signing_key_never_reaches_reht_gate_context() -> None:
    contract = _contract()
    record = _record(contract)
    expired = _trusted_key(valid_until=NOW - timedelta(seconds=1))
    with pytest.raises(GateAttestationInputError, match="not valid when"):
        build_reht_gate_context(
            [record],
            trusted_signing_keys=_registry(expired),
            now=NOW,
        )


def test_revoked_signing_key_never_reaches_reht_gate_context() -> None:
    contract = _contract()
    record = _record(contract)
    verify_now = NOW + timedelta(minutes=2)
    revoked = _trusted_key(
        revoked_at=NOW + timedelta(minutes=1),
        revocation_ref="revocation:approval-key-1",
    )
    with pytest.raises(GateAttestationInputError, match="has been revoked"):
        build_reht_gate_context(
            [record],
            trusted_signing_keys=_registry(revoked),
            now=verify_now,
        )


def test_gate_for_old_action_contract_cannot_authorize_modified_action() -> None:
    approved_contract = _contract()
    record = _record(approved_contract)
    fragment = build_reht_gate_context(
        [record],
        trusted_signing_keys=_registry(),
        now=NOW,
    )
    modified_contract = _contract(requested_value="different-effect")
    result = RealReht().authorize(_ctx(fragment), modified_contract)
    assert result.decision == "DENY"
    assert "exact action contract" in (result.reason or "")


def test_gate_for_prior_execution_nonce_cannot_authorize_new_attempt() -> None:
    contract = _contract()
    record = _record(contract, execution_nonce="nonce-7")
    fragment = build_reht_gate_context(
        [record],
        trusted_signing_keys=_registry(),
        now=NOW,
    )
    result = RealReht().authorize(
        _ctx(fragment, execution_nonce="nonce-8"),
        contract,
    )
    assert result.decision == "DENY"
    assert "current execution nonce" in (result.reason or "")
