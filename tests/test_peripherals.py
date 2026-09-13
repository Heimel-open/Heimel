from datetime import datetime, timedelta, timezone

import pytest

from paios.peripherals import (
    AdmissibilityStatus,
    EvidenceEnvelope,
    EvidenceStage,
    ObservationEnvelope,
    SourceRef,
    admit_observation,
    assert_adapter_conformance,
)


NOW = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)


def make_observation(**overrides):
    data = dict(
        observation_id="obs-001",
        subject_id="person-001",
        observed_at=NOW,
        received_at=NOW + timedelta(seconds=1),
        modality="audio",
        source=SourceRef(provider="example-mic", adapter="example-audio-v1", device_id="mic-1"),
        payload={"transcript": "hello"},
        provenance={"capture_hash": "sha256:abc"},
        confidence=0.91,
        mandate_id="mandate-1",
        purpose="conversation-context",
        integrity_ref="sha256:def",
    )
    data.update(overrides)
    return ObservationEnvelope(**data)


def test_valid_normalized_observation_is_green_raw_evidence():
    result = admit_observation(make_observation())
    assert result.status is AdmissibilityStatus.GREEN
    assert result.admitted is True
    assert result.observation.stage is EvidenceStage.RAW


def test_missing_mandate_does_not_become_unrestricted_access():
    result = admit_observation(make_observation(mandate_id=None, purpose=None))
    assert result.status is AdmissibilityStatus.AMBER
    assert result.admitted is False
    assert any("not disclosed" in reason for reason in result.reasons)


def test_adapter_cannot_emit_validated_or_canonical_state_directly():
    result = admit_observation(make_observation(stage=EvidenceStage.CANONICAL))
    assert result.status is AdmissibilityStatus.RED
    assert "adapter output must enter as RAW evidence" in result.reasons


def test_observation_without_provenance_fails_closed():
    result = admit_observation(make_observation(provenance={}))
    assert result.status is AdmissibilityStatus.RED
    assert "provenance is required" in result.reasons


def test_future_received_ordering_violation_fails_closed():
    result = admit_observation(
        make_observation(received_at=NOW - timedelta(seconds=1))
    )
    assert result.status is AdmissibilityStatus.RED
    assert "received_at cannot precede observed_at" in result.reasons


def test_invalid_confidence_fails_closed():
    result = admit_observation(make_observation(confidence=1.01))
    assert result.status is AdmissibilityStatus.RED
    assert "confidence must be between 0 and 1" in result.reasons


def test_canonical_evidence_requires_supporting_evidence():
    evidence = EvidenceEnvelope(
        observation_id="obs-001",
        stage=EvidenceStage.CANONICAL,
        confidence=0.99,
        provenance={"validator": "cross-check-v1"},
    )
    assert "canonical promotion requires supporting evidence" in evidence.validate()


def test_supported_canonical_evidence_is_structurally_valid():
    evidence = EvidenceEnvelope(
        observation_id="obs-001",
        stage=EvidenceStage.CANONICAL,
        confidence=0.99,
        provenance={"validator": "cross-check-v1"},
        support_refs=("obs-001", "obs-002"),
        rationale="independent corroboration",
    )
    assert evidence.validate() == ()


class GoodAdapter:
    adapter_name = "browser-extension-v1"

    def normalize(self, payload):
        return make_observation(
            modality="browser",
            payload=payload,
            source=SourceRef(provider="browser", adapter=self.adapter_name),
        )


class BadAdapter:
    adapter_name = ""


def test_provider_adapter_conforms_to_single_narrow_waist():
    adapter = GoodAdapter()
    assert_adapter_conformance(adapter)
    normalized = adapter.normalize({"url": "https://example.test"})
    assert isinstance(normalized, ObservationEnvelope)
    assert normalized.source.provider == "browser"


def test_nonconforming_adapter_is_rejected():
    with pytest.raises(TypeError):
        assert_adapter_conformance(BadAdapter())
