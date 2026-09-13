from pydantic import ValidationError
import pytest

from valo_edge.contracts import EdgeActionCommitmentV1
from valo_edge.vaig import (
    DeviceAttestationEvidenceV1,
    EvidenceGapSeverity,
    EvidenceRequirementsV1,
    LocalVaigEdge,
    ModelSignalV1,
    PhysicalStateEvidenceV1,
    SensorEvidenceV1,
)
from valo_edge.vaig.evaluator import _sensor_commitment


EVALUATED_AT = "2026-08-05T12:00:01Z"


def _sensor(
    source_id: str = "camera-1",
    digest: str = "sha256:frame-1",
    observed_at: str = "2026-08-05T12:00:00Z",
) -> SensorEvidenceV1:
    return SensorEvidenceV1(
        source_id=source_id,
        source_type="camera",
        evidence_digest=digest,
        observed_at_iso=observed_at,
        provenance=["camera-1", "detector-v1"],
    )


def _state() -> PhysicalStateEvidenceV1:
    return PhysicalStateEvidenceV1(state={"door_closed": True, "temperature_c": 21.5})


def _proposal(
    *,
    model_hash: str = "sha256:model",
    sensors: list[SensorEvidenceV1] | None = None,
    state: PhysicalStateEvidenceV1 | None = None,
) -> EdgeActionCommitmentV1:
    sensors = sensors or [_sensor()]
    state = state or _state()
    return EdgeActionCommitmentV1(
        proposal_id="proposal-1",
        device_id="device-1",
        action_type="OPEN_VALVE",
        parameters={"percent": 20},
        model_hash=model_hash,
        firmware_hash="sha256:firmware",
        runtime_hash="sha256:runtime",
        sensor_evidence_digest=_sensor_commitment(sensors),
        physical_state_digest=state.compute_digest(),
        authority_envelope_digest="sha256:authority",
        boot_epoch="boot-1",
        sequence=1,
        nonce="nonce-1",
        issued_at_iso="2026-08-05T12:00:00Z",
        valid_until_iso="2026-08-05T12:00:05Z",
        signer_key_id="device-key-1",
    )


def _attestation() -> DeviceAttestationEvidenceV1:
    return DeviceAttestationEvidenceV1(
        device_id="device-1",
        hardware_attestation_hash="sha256:hardware",
        firmware_hash="sha256:firmware",
        runtime_hash="sha256:runtime",
        boot_epoch="boot-1",
        key_id="device-key-1",
    )


def test_complete_model_backed_evidence():
    sensors = [_sensor()]
    state = _state()
    result = LocalVaigEdge().evaluate(
        _proposal(sensors=sensors, state=state),
        device_attestation=_attestation(),
        sensors=sensors,
        physical_state=state,
        model_signal=ModelSignalV1(
            model_hash="sha256:model",
            confidence=0.94,
            uncertainty=0.06,
            calibration="temperature-v1",
        ),
        requirements=EvidenceRequirementsV1(
            required_state_keys=["door_closed"],
            expected_state={"door_closed": True},
            max_freshness_ms=2_000,
        ),
        evaluated_at_iso=EVALUATED_AT,
    )
    assert result.is_complete()
    assert result.evidence.completeness is True
    assert result.evidence.freshness_ms == 1000
    assert not hasattr(result, "decision")
    assert result.evidence.observed_state["vaig"]["model_confidence"] == 0.94


def test_model_free_path_is_complete_when_model_is_not_used():
    sensors = [_sensor()]
    state = _state()
    result = LocalVaigEdge().evaluate(
        _proposal(model_hash="", sensors=sensors, state=state),
        device_attestation=_attestation(),
        sensors=sensors,
        physical_state=state,
        requirements=EvidenceRequirementsV1(require_model=False),
        evaluated_at_iso=EVALUATED_AT,
    )
    assert result.is_complete()
    assert result.evidence.model_hash == ""
    assert result.evidence.observed_state["vaig"]["model_used"] is False


def test_proposal_with_model_requires_model_evidence():
    sensors = [_sensor()]
    state = _state()
    result = LocalVaigEdge().evaluate(
        _proposal(sensors=sensors, state=state),
        device_attestation=_attestation(),
        sensors=sensors,
        physical_state=state,
        evaluated_at_iso=EVALUATED_AT,
    )
    assert not result.is_complete()
    assert any(
        gap.field == "model_signal" and gap.severity == EvidenceGapSeverity.MISSING
        for gap in result.gaps
    )


def test_missing_required_evidence_is_explicit_and_never_a_decision():
    proposal = _proposal(model_hash="")
    result = LocalVaigEdge().evaluate(
        proposal,
        requirements=EvidenceRequirementsV1(min_sensor_sources=1),
        evaluated_at_iso=EVALUATED_AT,
    )
    fields = {gap.field for gap in result.gaps}
    assert {"device_attestation", "sensor_sources", "physical_state_digest"} <= fields
    assert result.evidence.completeness is False
    assert not hasattr(result.evidence, "decision")


def test_stale_and_future_sensor_evidence_are_reported():
    stale = _sensor("camera-stale", "sha256:stale", "2026-08-05T11:59:00Z")
    future = _sensor("camera-future", "sha256:future", "2026-08-05T12:00:02Z")
    state = _state()
    proposal = _proposal(model_hash="", sensors=[stale, future], state=state)
    result = LocalVaigEdge().evaluate(
        proposal,
        device_attestation=_attestation(),
        sensors=[stale, future],
        physical_state=state,
        requirements=EvidenceRequirementsV1(max_freshness_ms=1_000),
        evaluated_at_iso=EVALUATED_AT,
    )
    assert any(gap.severity == EvidenceGapSeverity.STALE for gap in result.gaps)
    assert any("from the future" in gap.reason for gap in result.gaps)


def test_hash_and_state_mismatches_are_contradictions():
    sensors = [_sensor()]
    state = _state()
    proposal = _proposal(sensors=sensors, state=state).model_copy(
        update={
            "firmware_hash": "sha256:other-firmware",
            "runtime_hash": "sha256:other-runtime",
            "sensor_evidence_digest": "sha256:other-sensors",
            "physical_state_digest": "sha256:other-state",
        }
    )
    result = LocalVaigEdge().evaluate(
        proposal,
        device_attestation=_attestation(),
        sensors=sensors,
        physical_state=state,
        model_signal=ModelSignalV1(model_hash="sha256:wrong-model", confidence=0.5),
        evaluated_at_iso=EVALUATED_AT,
    )
    contradiction_fields = {
        gap.field for gap in result.gaps if gap.severity == EvidenceGapSeverity.CONTRADICTORY
    }
    assert {
        "firmware_hash",
        "runtime_hash",
        "model_hash",
        "sensor_evidence_digest",
        "physical_state_digest",
    } <= contradiction_fields


def test_duplicate_sensor_id_with_conflicting_digest_is_rejected():
    sensors = [
        _sensor("camera-1", "sha256:a"),
        _sensor("camera-1", "sha256:b"),
    ]
    state = _state()
    result = LocalVaigEdge().evaluate(
        _proposal(model_hash="", sensors=sensors, state=state),
        device_attestation=_attestation(),
        sensors=sensors,
        physical_state=state,
        evaluated_at_iso=EVALUATED_AT,
    )
    assert any("conflicting digests" in gap.reason for gap in result.gaps)


def test_required_and_expected_physical_state_are_checked():
    sensors = [_sensor()]
    state = PhysicalStateEvidenceV1(state={"door_closed": False})
    result = LocalVaigEdge().evaluate(
        _proposal(model_hash="", sensors=sensors, state=state),
        device_attestation=_attestation(),
        sensors=sensors,
        physical_state=state,
        requirements=EvidenceRequirementsV1(
            required_state_keys=["pressure_ok"],
            expected_state={"door_closed": True},
        ),
        evaluated_at_iso=EVALUATED_AT,
    )
    assert any("pressure_ok" in gap.reason for gap in result.gaps)
    assert any("door_closed" in gap.reason for gap in result.gaps)
    assert result.evidence.observed_state["vaig"]["state_consistent"] is False


def test_sensor_order_does_not_change_commitment_or_evidence_digest():
    left = [_sensor("b", "sha256:b"), _sensor("a", "sha256:a")]
    right = list(reversed(left))
    state = _state()
    left_result = LocalVaigEdge().evaluate(
        _proposal(model_hash="", sensors=left, state=state),
        device_attestation=_attestation(),
        sensors=left,
        physical_state=state,
        evaluated_at_iso=EVALUATED_AT,
    )
    right_result = LocalVaigEdge().evaluate(
        _proposal(model_hash="", sensors=right, state=state),
        device_attestation=_attestation(),
        sensors=right,
        physical_state=state,
        evaluated_at_iso=EVALUATED_AT,
    )
    assert _sensor_commitment(left) == _sensor_commitment(right)
    assert left_result.evidence.compute_digest() == right_result.evidence.compute_digest()


def test_confidence_and_uncertainty_are_bounded():
    with pytest.raises(ValidationError):
        ModelSignalV1(model_hash="sha256:model", confidence=1.1)
