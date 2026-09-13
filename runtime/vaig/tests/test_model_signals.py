"""Tests for native model signal plumbing."""

import json
from types import SimpleNamespace

import pytest

from vaig.ensemble import DistrustLevel, VAIGEnsemble
from vaig.instruments import activation_probe, logprob_scorer
from vaig.instruments.result import InstrumentStatus
from vaig.model_signals import ModelSignalBundle
from vaig.orchestrator import VAIGOrchestrator


def signal_bundle(**overrides):
    values = {
        "provider": "test-provider",
        "model_id": "model-x",
        "model_version": "2026-07-29",
        "generation_config_hash": "sha256:config",
        "response_id": "response-1",
    }
    values.update(overrides)
    return ModelSignalBundle(**values)


def test_signal_bundle_validates_logprobs():
    with pytest.raises(ValueError, match="<= 0"):
        signal_bundle(logprobs=(-0.2, 0.1))


def test_signal_bundle_exposes_digests_not_raw_signals():
    bundle = signal_bundle(
        logprobs=(-0.2, -0.4),
        hidden_states=((0.1, 0.2), (0.2, 0.3)),
    )

    metadata = bundle.audit_metadata()

    assert metadata["signals"]["logprobs_digest"].startswith("sha256:")
    assert metadata["signals"]["hidden_states_digest"].startswith("sha256:")
    assert "logprobs" not in metadata["signals"]
    assert "hidden_states" not in metadata["signals"]


def test_logprob_slot_is_unavailable_without_native_logprobs(tmp_path):
    ensemble = VAIGEnsemble(log_path=str(tmp_path / "audit.jsonl"))
    ensemble.instruments = {
        "logprob_scorer": logprob_scorer.TokenEntropyLogprobScorer(),
    }

    result = ensemble.evaluate(
        prompt="Question",
        response="Confident prose.",
        active_slots={"logprob_scorer"},
    )

    measurement = result.instrument_results["logprob_scorer"]
    assert measurement.status is InstrumentStatus.UNAVAILABLE
    assert measurement.raw_score is None
    assert "logprobs" in measurement.required_inputs
    assert "logprob_scorer" not in result.scores


def test_required_logprob_slot_fails_closed_without_signal(tmp_path):
    ensemble = VAIGEnsemble(log_path=str(tmp_path / "audit.jsonl"))
    ensemble.instruments = {
        "logprob_scorer": logprob_scorer.TokenEntropyLogprobScorer(),
    }

    result = ensemble.evaluate(
        prompt="Question",
        response="Answer",
        active_slots={"logprob_scorer"},
        required_slots={"logprob_scorer"},
    )

    assert result.level is DistrustLevel.HALT
    assert result.aggregation.abstained is True
    assert result.required_unmeasured == ("logprob_scorer",)


def test_native_logprobs_are_measured_and_hash_bound(tmp_path):
    bundle = signal_bundle(logprobs=(-0.2, -0.4, -0.6))
    ensemble = VAIGEnsemble(log_path=str(tmp_path / "audit.jsonl"))
    ensemble.instruments = {
        "logprob_scorer": logprob_scorer.TokenEntropyLogprobScorer(),
    }

    result = ensemble.evaluate(
        prompt="Question",
        response="Answer",
        active_slots={"logprob_scorer"},
        model_signals=bundle,
    )

    measurement = result.instrument_results["logprob_scorer"]
    assert measurement.status is InstrumentStatus.MEASURED
    assert measurement.evidence_refs == (bundle.logprobs_digest,)
    assert measurement.version == "native-logprob-surprisal-v1"

    entry = ensemble.worm.read_all()[0]
    signals = entry["model_signal_binding"]["signals"]
    assert signals["logprobs_digest"] == bundle.logprobs_digest
    assert "logprobs" not in signals


def test_activation_with_hidden_states_but_no_calibration_is_uncalibrated(tmp_path):
    bundle = signal_bundle(hidden_states=((0.2, 0.3, 0.4),))
    ensemble = VAIGEnsemble(log_path=str(tmp_path / "audit.jsonl"))
    ensemble.instruments = {
        "activation_probe": activation_probe.GeometricDriftProbe(),
    }

    result = ensemble.evaluate(
        prompt="Question",
        response="Answer",
        active_slots={"activation_probe"},
        required_slots={"activation_probe"},
        model_signals=bundle,
    )

    measurement = result.instrument_results["activation_probe"]
    assert measurement.status is InstrumentStatus.UNCALIBRATED
    assert measurement.raw_score is None
    assert result.level is DistrustLevel.HALT
    assert result.aggregation.abstained is True


def test_calibrated_activation_is_measured_and_bound(tmp_path):
    bundle = signal_bundle(hidden_states=((0.2, 0.3, 0.4),))
    probe = activation_probe.GeometricDriftProbe(
        reference_centroid=[0.1, 0.2, 0.3],
        calibration_profile="local-model-domain-v1",
        normalization_scale=1.0,
    )
    ensemble = VAIGEnsemble(log_path=str(tmp_path / "audit.jsonl"))
    ensemble.instruments = {"activation_probe": probe}

    result = ensemble.evaluate(
        prompt="Question",
        response="Answer",
        active_slots={"activation_probe"},
        model_signals=bundle,
    )

    measurement = result.instrument_results["activation_probe"]
    assert measurement.status is InstrumentStatus.MEASURED
    assert measurement.calibration_profile == "local-model-domain-v1"
    assert measurement.evidence_refs == (bundle.hidden_states_digest,)

    entry = ensemble.worm.read_all()[0]
    serialized = json.dumps(entry)
    assert bundle.hidden_states_digest in serialized
    assert "[[0.2, 0.3, 0.4]]" not in serialized


def test_orchestrator_forwards_model_signal_bundle(tmp_path):
    bundle = signal_bundle(logprobs=(-0.2, -0.4))
    orchestrator = VAIGOrchestrator(
        log_path=str(tmp_path / "audit.jsonl"),
        with_cakm=False,
    )
    orchestrator.ensemble.instruments = {
        "logprob_scorer": logprob_scorer.TokenEntropyLogprobScorer(),
    }
    orchestrator.dirigent.conduct = lambda _terrain: SimpleNamespace(
        internal=["logprob_scorer"],
        external=[],
        bench=[],
        thresholds={},
        context_health=1.0,
        context_warning=None,
        context_warning_detail=None,
    )

    result = orchestrator.evaluate(
        prompt="Question",
        response="Answer",
        model_signals=bundle,
    )

    measurement = result.validation.instrument_results["logprob_scorer"]
    assert measurement.status is InstrumentStatus.MEASURED
    assert measurement.evidence_refs == (bundle.logprobs_digest,)
