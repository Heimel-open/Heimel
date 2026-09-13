"""P0.7: trajectory intake is accepted by the orchestrator and available to instruments.

Verifies that a supplied Trajectory is (a) consumed by an instrument that
declares requires_trajectory, (b) recorded on OrchestratorResult for REHT, and
(c) fails the dependent slot closed when no trajectory is supplied.
"""

from datetime import datetime, timezone

from vaig.orchestrator import VAIGOrchestrator
from vaig.trajectory import Trajectory, TrajectoryStep


def _traj(clean: bool = True) -> Trajectory:
    steps = [
        TrajectoryStep(
            step_id="1",
            prompt="What is the dose?",
            response="Let me check.",
            role="model",
            provenance="model",
            timestamp=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        ),
        TrajectoryStep(
            step_id="2",
            prompt="Check done.",
            response="Take 500mg.",
            role="model",
            provenance="model" if clean else "external-unverified",
            timestamp=datetime(2026, 1, 1, 12, 0, 5, tzinfo=timezone.utc),
        ),
    ]
    return Trajectory(steps=tuple(steps), trajectory_id="t-1")


def test_trajectory_consumed_by_instrument_and_recorded():
    orch = VAIGOrchestrator(log_path=":memory:")
    res = orch.evaluate(
        "What is the dose?", "Take 500mg.",
        trajectory=_traj(clean=True),
        required_slots={"trajectory_consistency"},
    )
    slot = res.validation.instrument_results["trajectory_consistency"]
    assert slot.status.value == "MEASURED"
    assert 0.0 <= float(res.validation.scores["trajectory_consistency"]) <= 1.0
    # recorded on the result for REHT
    assert res.trajectory is not None
    assert res.trajectory.step_count == 2
    assert res.trajectory.has_provenance is True


def test_trajectory_missing_fails_closed():
    orch = VAIGOrchestrator(log_path=":memory:")
    res = orch.evaluate("p", "r", required_slots={"trajectory_consistency"})
    slot = res.validation.instrument_results["trajectory_consistency"]
    assert slot.status.value == "UNAVAILABLE"
    assert "trajectory" in (slot.required_inputs or ())
    assert "trajectory_consistency" not in res.validation.scores


def test_ungoverned_provenance_scores_higher():
    orch = VAIGOrchestrator(log_path=":memory:")
    clean = orch.evaluate("p", "r", trajectory=_traj(clean=True),
                          required_slots={"trajectory_consistency"})
    dirty = orch.evaluate("p", "r", trajectory=_traj(clean=False),
                          required_slots={"trajectory_consistency"})
    c = float(clean.validation.scores["trajectory_consistency"])
    d = float(dirty.validation.scores["trajectory_consistency"])
    assert d > c
