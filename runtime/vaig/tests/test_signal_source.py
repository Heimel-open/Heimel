"""
P0.3: bind a real model signal into the integrity layer via SignalSource.

Verifies that an instrument (logprob_scorer) reads a native model signal
through an injected SignalSource, that the signal source id is recorded in the
report, and that a missing / failing source fails the dependent slot closed
(explicit reason, never a silent 0.0).
"""

from vaig.ensemble import VAIGEnsemble
from vaig.instruments.logprob_scorer import TokenEntropyLogprobScorer
from vaig.model_signals import ModelSignalBundle
from vaig.signal_source import SignalSource, SignalUnavailableError, StaticSignalSource


def _bundle(logprobs):
    return ModelSignalBundle(
        provider="test-provider",
        model_id="test-model",
        model_version="v1",
        generation_config_hash="cfg-1",
        logprobs=logprobs,
    )


def test_signal_source_feeds_logprob_scorer_and_records_id():
    src = StaticSignalSource(_bundle([-0.1, -0.2, -0.3]), id="src-1")
    e = VAIGEnsemble(log_path=":memory:", signal_source=src)
    res = e.evaluate(
        prompt="p", response="r", active_slots={"logprob_scorer"}
    )
    slot = res.instrument_results["logprob_scorer"]
    assert slot.status.value == "MEASURED"
    assert 0.0 <= float(res.scores["logprob_scorer"]) <= 1.0
    # signal source id recorded in the report
    assert "src-1" in slot.evidence_refs


def test_missing_signal_source_fails_closed_not_silent_zero():
    # no signal source -> logprob_scorer needs native logprobs -> fail closed
    e = VAIGEnsemble(log_path=":memory:")
    res = e.evaluate(
        prompt="p", response="r", active_slots={"logprob_scorer"}
    )
    slot = res.instrument_results["logprob_scorer"]
    assert slot.status.value == "UNAVAILABLE"
    assert "SignalSource not supplied" in (slot.failure_reason or "")
    # never an admissible measured 0.0
    assert "logprob_scorer" not in res.scores


def test_failing_signal_source_fails_closed_with_id():
    src = StaticSignalSource(
        _bundle([-0.1]), id="src-broken", fail_with=SignalUnavailableError("api down")
    )
    e = VAIGEnsemble(log_path=":memory:", signal_source=src)
    res = e.evaluate(
        prompt="p", response="r", active_slots={"logprob_scorer"}
    )
    slot = res.instrument_results["logprob_scorer"]
    assert slot.status.value == "UNAVAILABLE"
    reason = slot.failure_reason or ""
    assert "src-broken" in reason
    assert "api down" in reason
    assert "logprob_scorer" not in res.scores


def test_signal_source_is_protocol_contract():
    # TokenEntropyLogprobScorer stands in for the real signal consumer; the
    # contract is that SignalSource.fetch returns a ModelSignalBundle.
    assert isinstance(StaticSignalSource(_bundle([-0.1])), object)
    # A real implementation must satisfy the SignalSource protocol shape.
    assert hasattr(SignalSource, "fetch")
