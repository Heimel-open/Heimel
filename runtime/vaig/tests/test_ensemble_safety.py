"""Regression tests for VAIGEnsemble safety semantics."""

import hashlib

from vaig.ensemble import DistrustLevel, VAIGEnsemble
from vaig.instruments.result import InstrumentStatus


class FailingInstrument:
    def score(self, **kwargs):
        raise RuntimeError("boom")


class ZeroInstrument:
    requires_generate_fn = True

    def score(self, **kwargs):
        return 0.0


class NativeLogprobInstrument:
    def score(self, prompt, response, logprobs=None, **kwargs):
        assert prompt
        assert response
        assert logprobs == [-0.2, -0.4]
        return 0.25


def test_instrument_exception_fails_closed(tmp_path):
    ensemble = VAIGEnsemble(log_path=str(tmp_path / "audit.jsonl"))
    ensemble.instruments = {"schema": FailingInstrument()}

    result = ensemble.evaluate(
        prompt="can I transfer funds?",
        response="yes, executing now",
        active_slots={"schema"},
    )

    assert result.level == DistrustLevel.HALT
    assert result.should_halt is True
    assert result.scores["schema"] == 1.0
    assert result.instrument_errors == {"schema": "RuntimeError"}
    assert result.instrument_results["schema"].status is InstrumentStatus.ERROR
    assert result.instrument_results["schema"].raw_score is None

    entries = ensemble.worm.read_all()
    assert entries[0]["instrument_errors"] == {"schema": "RuntimeError"}
    assert entries[0]["instrument_results"]["schema"]["status"] == "ERROR"


def test_missing_generate_fn_is_unavailable_not_safe_zero(tmp_path):
    ensemble = VAIGEnsemble(log_path=str(tmp_path / "audit.jsonl"))
    ensemble.instruments = {"semantic_entropy": ZeroInstrument()}

    result = ensemble.evaluate(
        prompt="What happened?",
        response="One explanation.",
        active_slots={"semantic_entropy"},
    )

    measurement = result.instrument_results["semantic_entropy"]
    assert measurement.status is InstrumentStatus.UNAVAILABLE
    assert measurement.raw_score is None
    assert measurement.failure_reason == "Required generate_fn was not supplied."
    assert "semantic_entropy" not in result.scores
    assert result.combined_score == 0.0

    entries = ensemble.worm.read_all()
    stored = entries[0]["instrument_results"]["semantic_entropy"]
    assert stored["status"] == "UNAVAILABLE"
    assert stored["raw_score"] is None


def test_required_unmeasured_slot_fails_closed(tmp_path):
    ensemble = VAIGEnsemble(log_path=str(tmp_path / "audit.jsonl"))
    ensemble.instruments = {}

    result = ensemble.evaluate(
        prompt="Approve payment?",
        response="Approved.",
        active_slots=set(),
        required_slots={"logprob_scorer"},
    )

    assert result.instrument_results["logprob_scorer"].status is InstrumentStatus.UNAVAILABLE
    assert result.required_unmeasured == ("logprob_scorer",)
    assert result.level is DistrustLevel.HALT
    assert result.should_halt is True

    entries = ensemble.worm.read_all()
    assert entries[0]["required_unmeasured"] == ["logprob_scorer"]


def test_slot_specific_native_inputs_are_forwarded(tmp_path):
    ensemble = VAIGEnsemble(log_path=str(tmp_path / "audit.jsonl"))
    ensemble.instruments = {"logprob_scorer": NativeLogprobInstrument()}

    result = ensemble.evaluate(
        prompt="Question",
        response="Answer",
        active_slots={"logprob_scorer"},
        instrument_inputs={"logprob_scorer": {"logprobs": [-0.2, -0.4]}},
    )

    measurement = result.instrument_results["logprob_scorer"]
    assert measurement.status is InstrumentStatus.MEASURED
    assert measurement.raw_score == 0.25
    assert "logprobs" in measurement.supplied_inputs
    assert result.scores == {"logprob_scorer": 0.25}


def test_prompt_hash_is_stable_sha256(tmp_path):
    ensemble = VAIGEnsemble(log_path=str(tmp_path / "audit.jsonl"))
    ensemble.instruments = {}

    prompt = "stable audit hash"
    ensemble.evaluate(prompt=prompt, response="ok", active_slots=set())

    entries = ensemble.worm.read_all()
    assert entries[0]["prompt_sha256"] == hashlib.sha256(prompt.encode()).hexdigest()
    assert "prompt_hash" not in entries[0]
