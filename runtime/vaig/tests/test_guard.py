"""BlindspotGuard behaviour: abstention + agreement over model measurements."""

import pytest

from vaig.guard import BlindspotGuard
from vaig.instruments.result import InstrumentResult, InstrumentStatus


def _measured(slot, raw_score, self_judging=False, confidence=None):
    return InstrumentResult(
        slot=slot,
        status=InstrumentStatus.MEASURED,
        raw_score=raw_score,
        calibrated_risk=raw_score,
        implementation="test",
        self_judging=self_judging,
        confidence=confidence,
    )


def test_measured_non_self_judging_without_confidence_is_kept():
    results = {"probe": _measured("probe", 0.2, confidence=0.9)}
    guarded, report = BlindspotGuard().guard_results(results)
    assert guarded["probe"].status is InstrumentStatus.MEASURED
    assert not report.abstained


def test_self_judged_always_abstains_even_with_confidence():
    results = {
        "auditor": _measured("auditor", 0.7, self_judging=True, confidence=0.95)
    }
    guarded, report = BlindspotGuard().guard_results(results)
    assert guarded["auditor"].status is InstrumentStatus.UNCALIBRATED
    assert report.abstained_slots == {
        "auditor": "self_judged_without_independent_judge"
    }
    assert report.signal_trust == "PARTIAL"


def test_below_confidence_threshold_abstains():
    results = {"probe": _measured("probe", 0.5, confidence=0.2)}
    guarded, report = BlindspotGuard().guard_results(results, )
    assert guarded["probe"].status is InstrumentStatus.UNCALIBRATED
    assert report.abstained_slots == {"probe": "below_confidence_threshold"}


def test_low_agreement_reduces_signal_trust():
    results = {
        "entropy": _measured("entropy", 0.1, confidence=0.9),
        "similarity": _measured("similarity", 0.9, confidence=0.8),
    }
    guarded, report = BlindspotGuard().guard_results(results)
    assert guarded["entropy"].status is InstrumentStatus.MEASURED
    assert guarded["similarity"].status is InstrumentStatus.MEASURED
    assert report.low_agreement is True
    assert report.signal_trust == "REDUCED"


def test_high_agreement_is_full_trust():
    results = {
        "entropy": _measured("entropy", 0.2, confidence=0.9),
        "similarity": _measured("similarity", 0.25, confidence=0.8),
    }
    _, report = BlindspotGuard().guard_results(results)
    assert report.low_agreement is False
    assert report.signal_trust == "FULL"


def test_non_measured_results_pass_through():
    unavailable = InstrumentResult(
        slot="probe",
        status=InstrumentStatus.UNAVAILABLE,
        implementation="test",
    )
    guarded, report = BlindspotGuard().guard_results({"probe": unavailable})
    assert guarded["probe"].status is InstrumentStatus.UNAVAILABLE
    assert not report.abstained


def test_invalid_thresholds_rejected():
    with pytest.raises(ValueError):
        BlindspotGuard(abstain_confidence=1.5)
    with pytest.raises(ValueError):
        BlindspotGuard(disagreement_threshold=-0.1)
