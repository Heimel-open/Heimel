from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from vaig.continuity_assessment import (
    ASSESSOR_REF,
    ContinuityAssessmentError,
    SCHEMA_VERSION,
    SERVICE_ID,
    assess_continuity_request,
    canonical_digest,
)


NOW = datetime(2026, 8, 1, 15, 40, tzinfo=timezone.utc)


def request(*, kind="revalidation_checkpoint", integrity="verified", freshness=1.0):
    previous = "sha256:source"
    current = previous if kind == "revalidation_checkpoint" else "sha256:changed"
    changed_fields = [] if kind == "revalidation_checkpoint" else ["policy_snapshot"]
    trigger = {
        "trigger_id": "trigger-1",
        "tenant_id": "tenant-1",
        "action_case_id": "case-1",
        "action_case_hash": "sha256:case",
        "clearance_ref": "clearance-1",
        "trigger_kind": kind,
        "severity": "info" if kind == "revalidation_checkpoint" else "high",
        "source_ref": "publication-policy-registry:tenant-1:policy-1:1",
        "observer_ref": "runtime:commit-boundary",
        "observed_at": NOW.isoformat().replace("+00:00", "Z"),
        "previous_fingerprint": previous,
        "current_fingerprint": current,
        "changed_fields": changed_fields,
        "source_evidence_refs": ["policy-event-1"],
        "confidence": 1.0,
        "freshness": freshness,
        "integrity_status": integrity,
        "trigger_digest": "sha256:trigger",
    }
    payload = {
        "request_id": "request-1",
        "requester_ref": "execution-gateway:content",
        "basis": {
            "snapshot_id": "basis-1",
            "tenant_id": "tenant-1",
            "action_case_id": "case-1",
            "action_case_hash": "sha256:case",
            "clearance_ref": "clearance-1",
            "observed_at": (NOW - timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
            "authority_fingerprint": "sha256:authority",
            "policy_fingerprint": "sha256:policy",
            "evidence_fingerprint": "sha256:evidence",
            "context_fingerprint": "sha256:context",
            "state_fingerprint": "sha256:case",
            "assumption_fingerprint": None,
            "purpose_binding_ref": "purpose-binding-1",
            "dependency_fingerprints": [],
            "valid_until": (NOW + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
            "snapshot_digest": "sha256:basis",
        },
        "source_baseline": {
            "binding": {
                "tenant_id": "tenant-1",
                "action_case_id": "case-1",
                "action_case_hash": "sha256:case",
                "clearance_ref": "clearance-1",
                "observer_ref": "runtime:commit-boundary",
            },
            "captured_at": (NOW - timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
            "entries": [
                {
                    "domain": "policy",
                    "source_ref": "publication-policy-registry:tenant-1:policy-1:1",
                    "fingerprint": previous,
                    "evidence_refs": ["policy-event-1"],
                    "captured_at": (NOW - timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
                    "entry_digest": "sha256:entry",
                }
            ],
            "baseline_digest": "sha256:baseline",
        },
        "source_bundle": {
            "binding": {
                "tenant_id": "tenant-1",
                "action_case_id": "case-1",
                "action_case_hash": "sha256:case",
                "clearance_ref": "clearance-1",
                "observer_ref": "runtime:commit-boundary",
            },
            "observed_at": NOW.isoformat().replace("+00:00", "Z"),
            "observations": [
                {
                    "domain": "policy",
                    "source_ref": "publication-policy-registry:tenant-1:policy-1:1",
                    "expected_fingerprint": previous,
                    "current_fingerprint": current,
                    "observed_at": NOW.isoformat().replace("+00:00", "Z"),
                    "changed_fields": changed_fields,
                    "evidence_refs": ["policy-event-1"],
                    "integrity_status": integrity,
                    "trigger": None if kind == "revalidation_checkpoint" else trigger,
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
        "evidence_refs": ["policy-event-1"],
        "requested_at": NOW.isoformat().replace("+00:00", "Z"),
        "request_digest": "",
    }
    payload["request_digest"] = canonical_digest(
        {key: value for key, value in payload.items() if key != "request_digest"}
    )
    return payload


def test_stable_checkpoint_returns_no_material_change_only():
    payload = request()
    response = assess_continuity_request(
        payload,
        assessed_at=NOW + timedelta(seconds=1),
    )

    assessment = response["assessment"]
    assert response["schema_version"] == SCHEMA_VERSION
    assert response["service_id"] == SERVICE_ID
    assert response["request_ref"] == (
        "continuity-revalidation-request:" + payload["request_digest"]
    )
    assert assessment["materiality"] == "no_material_change"
    assert assessment["assessor_refs"] == [ASSESSOR_REF]
    assert assessment["confidence"] == 1.0
    assert assessment["bounded_modification_available"] is False
    assert "decision" not in response
    assert "clearance" not in response
    assert "racs_outcome" not in assessment


def test_source_drift_returns_material_change_without_authorization():
    response = assess_continuity_request(
        request(kind="policy_changed"),
        assessed_at=NOW + timedelta(seconds=1),
    )

    assessment = response["assessment"]
    assert assessment["materiality"] == "material_change"
    assert assessment["impact_dimensions"] == ["policy"]
    assert assessment["reason_codes"] == ["authoritative_source_drift_observed"]
    assert set(response) == {
        "schema_version",
        "service_id",
        "request_ref",
        "request_digest",
        "assessment",
    }


def test_unverified_or_stale_evidence_returns_insufficient_evidence():
    failed = assess_continuity_request(
        request(kind="policy_changed", integrity="failed"),
        assessed_at=NOW + timedelta(seconds=1),
    )
    stale = assess_continuity_request(
        request(kind="policy_changed", freshness=0.1),
        assessed_at=NOW + timedelta(seconds=1),
    )

    assert failed["assessment"]["materiality"] == "insufficient_evidence"
    assert stale["assessment"]["materiality"] == "insufficient_evidence"
    assert failed["assessment"]["confidence"] == 0.0


def test_tampered_request_digest_fails_closed():
    payload = request()
    payload["basis"]["clearance_ref"] = "other-clearance"

    with pytest.raises(ContinuityAssessmentError, match="request_digest"):
        assess_continuity_request(payload, assessed_at=NOW + timedelta(seconds=1))


def test_cross_case_trigger_fails_closed_even_with_recomputed_digest():
    payload = request(kind="policy_changed")
    payload["triggers"][0]["action_case_id"] = "other-case"
    payload["request_digest"] = canonical_digest(
        {key: value for key, value in payload.items() if key != "request_digest"}
    )

    with pytest.raises(ContinuityAssessmentError, match="decision basis"):
        assess_continuity_request(payload, assessed_at=NOW + timedelta(seconds=1))


def test_incomplete_source_coverage_fails_closed():
    payload = request()
    payload["source_bundle"]["observations"] = []
    payload["request_digest"] = canonical_digest(
        {key: value for key, value in payload.items() if key != "request_digest"}
    )

    with pytest.raises(ContinuityAssessmentError, match="exactly cover"):
        assess_continuity_request(payload, assessed_at=NOW + timedelta(seconds=1))


def test_checkpoint_cannot_conceal_drift():
    payload = request()
    payload["triggers"][0]["current_fingerprint"] = "sha256:changed"
    payload["request_digest"] = canonical_digest(
        {key: value for key, value in payload.items() if key != "request_digest"}
    )

    with pytest.raises(ContinuityAssessmentError, match="cannot conceal"):
        assess_continuity_request(payload, assessed_at=NOW + timedelta(seconds=1))


def test_assessment_digest_is_canonical_and_tamper_evident():
    assessment = assess_continuity_request(
        request(), assessed_at=NOW + timedelta(seconds=1)
    )["assessment"]
    expected = canonical_digest(
        {
            key: value
            for key, value in assessment.items()
            if key != "assessment_digest"
        }
    )
    assert assessment["assessment_digest"] == expected

    tampered = deepcopy(assessment)
    tampered["materiality"] = "material_change"
    assert tampered["assessment_digest"] != canonical_digest(
        {
            key: value
            for key, value in tampered.items()
            if key != "assessment_digest"
        }
    )
