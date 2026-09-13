import pytest
from pydantic import ValidationError

from valo_edge.adapters.ruview import RuViewAdapter, RuViewObservationV1


def _observation(**updates) -> RuViewObservationV1:
    values = {
        "source_id": "ruview-node-7",
        "observed_at_iso": "2026-08-09T20:00:00Z",
        "environment_id": "room-a",
        "calibration_id": "room-a-cal-3",
        "pipeline_version": "ruview-v0.7",
        "presence": True,
        "motion_score": 0.42,
        "breathing_bpm": 14.0,
        "heart_rate_bpm": 68.0,
        "occupancy_estimate": 1,
        "signal_quality": 0.91,
        "confidence": 0.87,
        "model_hash": "sha256:ruview-model",
        "witness_digest": "ed25519:witness-42",
    }
    values.update(updates)
    return RuViewObservationV1(**values)


def test_ruview_maps_to_existing_edge_evidence_contracts():
    bundle = RuViewAdapter(expected_environment_id="room-a", require_witness=True).adapt(
        _observation()
    )

    assert bundle.sensor.source_id == "ruview-node-7"
    assert bundle.sensor.source_type == "wifi-csi/ruview"
    assert bundle.sensor.evidence_digest.startswith("sha256:")
    assert "environment:room-a" in bundle.sensor.provenance
    assert "calibration:room-a-cal-3" in bundle.sensor.provenance
    assert "witness:ed25519:witness-42" in bundle.sensor.provenance
    assert bundle.physical_state.state["ruview.presence"] is True
    assert bundle.physical_state.state["ruview.heart_rate_bpm"] == 68.0
    assert bundle.model_signal is not None
    assert bundle.model_signal.model_hash == "sha256:ruview-model"
    assert bundle.model_signal.confidence == 0.87
    assert not hasattr(bundle, "decision")


def test_same_observation_has_same_evidence_digest():
    adapter = RuViewAdapter()
    left = adapter.adapt(_observation()).sensor.evidence_digest
    right = adapter.adapt(_observation()).sensor.evidence_digest
    assert left == right


def test_signal_only_observation_does_not_invent_model_evidence():
    bundle = RuViewAdapter().adapt(
        _observation(model_hash="", confidence=None, witness_digest="")
    )
    assert bundle.model_signal is None


def test_environment_binding_fails_closed():
    with pytest.raises(ValueError, match="environment"):
        RuViewAdapter(expected_environment_id="room-b").adapt(_observation())


def test_required_witness_fails_closed():
    with pytest.raises(ValueError, match="witness"):
        RuViewAdapter(require_witness=True).adapt(_observation(witness_digest=""))


def test_simulated_input_is_rejected_by_default():
    with pytest.raises(ValueError, match="simulated"):
        RuViewAdapter().adapt(_observation(simulated=True))


def test_explicit_simulation_stays_non_physical_evidence():
    bundle = RuViewAdapter(allow_simulated=True).adapt(_observation(simulated=True))
    assert bundle.physical_state.state["ruview.simulated"] is True
    assert bundle.physical_state.contradictions == [
        "RuView observation is simulated and cannot establish physical reality"
    ]


def test_timestamp_requires_timezone():
    with pytest.raises(ValidationError, match="timezone"):
        _observation(observed_at_iso="2026-08-09T20:00:00")


def test_environment_calibration_and_pipeline_are_mandatory():
    with pytest.raises(ValidationError, match="binding"):
        _observation(calibration_id="")


def test_empty_observation_is_rejected():
    with pytest.raises(ValidationError, match="at least one"):
        _observation(
            presence=None,
            motion_score=None,
            breathing_bpm=None,
            heart_rate_bpm=None,
            fall_detected=None,
            occupancy_estimate=None,
            signal_quality=None,
        )
