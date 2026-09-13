"""QC tests for BARO Behavioral Convergence Monitor (valo-platform #131)."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.valo_platform.baro_behavioral_convergence import (
    BehavioralConvergenceMonitor,
    BehavioralConvergenceSignal,
    ConvergenceRisk,
)


def test_empty_window_is_low_risk():
    sig = BehavioralConvergenceMonitor().observe_window([])
    assert isinstance(sig, BehavioralConvergenceSignal)
    assert sig.risk == ConvergenceRisk.LOW


def test_herding_detected_when_actions_converge():
    decisions = [
        {"action": "approve", "model": "gpt", "source": "A", "overridden": False}
        for _ in range(10)
    ]
    sig = BehavioralConvergenceMonitor().observe_window(decisions)
    assert sig.monoculture_index >= 0.9
    assert sig.herding_risk >= 1.0
    assert sig.diversity_score <= 0.1
    assert sig.risk in (ConvergenceRisk.HIGH, ConvergenceRisk.CRITICAL)


def test_diverse_actions_stay_low_risk():
    decisions = [
        {"action": f"a{i}", "model": f"m{i}", "source": f"s{i}", "overridden": True}
        for i in range(10)
    ]
    sig = BehavioralConvergenceMonitor().observe_window(decisions)
    assert sig.monoculture_index <= 0.2
    assert sig.cognitive_dependency_index == 0.0  # all overridden -> low dependency
    assert sig.risk == ConvergenceRisk.LOW


def test_cognitive_dependency_rises_when_no_overrides():
    decisions = [
        {"action": "approve", "model": "gpt", "source": "A", "overridden": False}
        for _ in range(10)
    ]
    sig = BehavioralConvergenceMonitor().observe_window(decisions)
    assert sig.cognitive_dependency_index == 1.0  # zero human overrides


def test_source_concentration_hhi():
    # All same model/source -> HHI = 1.0
    decisions = [{"action": "x", "model": "gpt", "source": "A"} for _ in range(5)]
    sig = BehavioralConvergenceMonitor().observe_window(decisions)
    assert sig.source_concentration == 1.0


def test_feedback_loop_risk_counts_reality_change():
    decisions = [
        {"action": "x", "model": "gpt", "source": "A",
         "predicted_reality_before": "p1", "observed_reality_after": "p2"},
        {"action": "y", "model": "gpt", "source": "A",
         "predicted_reality_before": "q1", "observed_reality_after": "q1"},
    ]
    sig = BehavioralConvergenceMonitor().observe_window(decisions)
    assert sig.feedback_loop_risk == 0.5


def test_reality_package_fragment_shape():
    sig = BehavioralConvergenceMonitor().observe_window(
        [{"action": "approve", "model": "gpt", "source": "A", "overridden": False}])
    pkg = sig.as_reality_package()
    for key in ("convergence_score", "diversity_score", "source_concentration",
                "model_correlation", "cognitive_dependency_index", "herding_risk",
                "monoculture_index", "risk", "observer"):
        assert key in pkg
    assert pkg["observer"] == "baro_behavioral_convergence"


def test_observational_only_no_decision():
    # Monitor must never output an admissibility decision.
    sig = BehavioralConvergenceMonitor().observe_window(
        [{"action": "approve", "model": "gpt", "source": "A"}])
    assert isinstance(sig, BehavioralConvergenceSignal)
    assert not hasattr(sig, "admissible")
