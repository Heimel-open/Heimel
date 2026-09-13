from datetime import datetime, timedelta, timezone

import pytest

from vaig.continuity_assessment import (
    ContinuityAssessmentError,
    canonical_digest,
)
from vaig.continuity_wire import (
    WIRE_SCHEMA_VERSION,
    assess_continuity_wire,
)


NOW = datetime(2026, 8, 1, 15, 45, tzinfo=timezone.utc)


def request():
    trigger = {
        "trigger_id": "checkpoint-1",
        "tenant_id": "tenant-1",
        "action_case_id": "case-1",
        "action_case_hash": "sha256:case",
        "clearance_ref": "clearance-1",
        "trigger_kind": "revalidation_checkpoint",
        "severity": "info",
        "source_ref": "policy:1",
        "observer_ref": "runtime:1",
        "observed_at": NOW.isoformat().replace("+00:00", "Z"),
        "previous_fingerprint": "sha256:policy-source",
        "current_fingerprint": "sha256:policy-source",
        "changed_fields": [],
        "source_evidence_refs": ["evidence:policy"],
        "confidence": 1.0,
        "freshness": 1.0,
        "integrity_status": "verified",
        "trigger_digest": "sha256:trigger",
    }
    binding = {
        "tenant_id": "tenant-1",
        "action_case_id": "case-1",
        "action_case_hash": "sha256:case",
        "clearance_ref": "clearance-1",
        "observer_ref": "runtime:1",
    }
    payload = {
        "request_id": "request-1",
        "requester_ref": "gateway:1",
        "basis": {
            "snapshot_id": "basis-1",
            "tenant_id": "tenant-1",
            "action_case_id": "case-1",
            "action_case_hash": "sha256:case",
            "clearance_ref": "clearance-1",
            "observed_at": (NOW - timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
            "authority_fingerprint": "sha256:authority",
            "policy_fingerprint": "sha256:policy",
            "evidence_fingerprint": "sha256:evidence",
            "context_fingerprint": "sha256:context",
            "state_fingerprint": "sha256:case",
            "assumption_fingerprint": None,
            "purpose_binding_ref": "purpose:1",
            "dependency_fingerprints": [],
            "valid_until": (NOW + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
            "snapshot_digest": "sha256:basis",
        },
        "source_baseline": {
            "binding": binding,
            "captured_at": (NOW - timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
            "entries": [
                {
                    "domain": "policy",
                    "source_ref": "policy:1",
                    "fingerprint": "sha256:policy-source",
                    "evidence_refs": ["evidence:policy"],
                    "captured_at": (NOW - timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
                    "entry_digest": "sha256:entry",
                }
            ],
            "baseline_digest": "sha256:baseline",
        },
        "source_bundle": {
            "binding": binding,
            "observed_at": NOW.isoformat().replace("+00:00", "Z"),
            "observations": [
                {
                    "domain": "policy",
                    "source_ref": "policy:1",
                    "expected_fingerprint": "sha256:policy-source",
                    "current_fingerprint": "sha256:policy-source",
                    "observed_at": NOW.isoformat().replace("+00:00", "Z"),
                    "changed_fields": [],
                    "evidence_refs": ["evidence:policy"],
                    "integrity_status": "verified",
                    "trigger": None,
                    "observation_digest": "sha256:observation",
                }
            ],
            "bundle_digest": "sha256:bundle",
        },
        "current_fingerprints": {
            "authority": "sha256:authority",
            "policy": "sha256:policy",
            "context": "sha256:context",
            "state": "sha256:case",
            "evidence": "sha256:evidence",
            "fingerprint_digest": "sha256:fingerprints",
        },
        "triggers": [trigger],
        "evidence_refs": ["evidence:policy"],
        "requested_at": NOW.isoformat().replace("+00:00", "Z"),
        "request_digest": "",
    }
    payload["request_digest"] = canonical_digest(
        {key: value for key, value in payload.items() if key != "request_digest"}
    )
    return payload


def wire(**changes):
    payload = {
        "schema_version": WIRE_SCHEMA_VERSION,
        "assessed_at": NOW.isoformat().replace("+00:00", "Z"),
        "request": request(),
    }
    payload.update(changes)
    return payload


def test_wire_binds_assessment_to_exact_gateway_checkpoint_time():
    response = assess_continuity_wire(wire())
    assert response["assessment"]["assessed_at"] == "2026-08-01T15:45:00Z"
    assert response["assessment"]["materiality"] == "no_material_change"


def test_wire_rejects_unknown_schema_and_extra_fields():
    with pytest.raises(ContinuityAssessmentError, match="unsupported"):
        assess_continuity_wire(wire(schema_version="other/1"))

    payload = wire()
    payload["override_authority"] = "manager"
    with pytest.raises(ContinuityAssessmentError, match="contain only"):
        assess_continuity_wire(payload)


def test_wire_rejects_naive_or_predating_assessment_time():
    with pytest.raises(ContinuityAssessmentError, match="timezone-aware"):
        assess_continuity_wire(wire(assessed_at="2026-08-01T15:45:00"))

    with pytest.raises(ContinuityAssessmentError, match="cannot predate"):
        assess_continuity_wire(
            wire(
                assessed_at=(NOW - timedelta(seconds=1))
                .isoformat()
                .replace("+00:00", "Z")
            )
        )


def test_wire_rejects_non_object_request():
    with pytest.raises(ContinuityAssessmentError, match="request must be an object"):
        assess_continuity_wire(wire(request=[]))
