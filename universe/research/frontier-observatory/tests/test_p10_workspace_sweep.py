import importlib.util
import sys
from pathlib import Path

import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "experiments"
    / "P10_Transformer_Workspace_Dynamics"
    / "sweep_falsifier.py"
)
SPEC = importlib.util.spec_from_file_location("sweep_falsifier", MODULE_PATH)
sweep = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = sweep
SPEC.loader.exec_module(sweep)


def obs(
    phase,
    workspace,
    *,
    trace_id="trace",
    targets=("goal",),
    disconfirming=("counter",),
    tau=0.7,
):
    return sweep.SweepObservation(
        phase=phase,
        workspace=workspace,
        trace_id=trace_id,
        targets=frozenset(targets),
        disconfirming=frozenset(disconfirming),
        tau=tau,
    )


def consistent_trace():
    return [
        obs(
            "BROAD_SCAN",
            {
                "goal": 0.15,
                "counter": 0.15,
                "alt": 0.15,
                "x": 0.15,
                "y": 0.20,
                "z": 0.20,
            },
        ),
        obs("TARGET_LOCK", {"goal": 0.80, "alt": 0.10, "x": 0.10}),
        obs("DISCONFIRMING_SWEEP", {"counter": 0.55, "goal": 0.25, "alt": 0.20}),
        obs("UNCERTAINTY_MAP", {"counter": 0.35, "goal": 0.35, "unknown": 0.30}),
        obs("CANDIDATE_SET", {"goal": 0.45, "counter": 0.35, "alt": 0.20}),
        obs("CANDIDATE_SET", {"goal": 0.46, "counter": 0.34, "alt": 0.20}),
    ]


def falsifying_trace():
    broad = {
        "goal": 0.15,
        "counter": 0.15,
        "alt": 0.15,
        "x": 0.15,
        "y": 0.20,
        "z": 0.20,
    }
    return [
        obs("BROAD_SCAN", broad),
        obs("TARGET_LOCK", broad),
        obs("DISCONFIRMING_SWEEP", broad),
        obs("UNCERTAINTY_MAP", broad),
        obs("CANDIDATE_SET", {"goal": 0.9, "counter": 0.1}),
        obs("CANDIDATE_SET", {"alt": 0.9, "x": 0.1}),
    ]


def test_consistent_trace_is_not_mislabeled_as_validation():
    results = sweep.evaluate_hypothesis(consistent_trace(), goldilocks=(0.55, 0.85))
    assert all(result.status == sweep.CONSISTENT for result in results)
    assert sweep.overall_status(results) == "NOT_FALSIFIED_BY_TRACE"


def test_null_like_trace_falsifies_phase_conditioned_predictions():
    results = sweep.evaluate_hypothesis(falsifying_trace(), goldilocks=(0.55, 0.85))
    statuses = {result.criterion: result.status for result in results}
    assert statuses["JFS-1 target alignment"] == sweep.FALSIFIED
    assert statuses["JFS-2 workspace concentration"] == sweep.FALSIFIED
    assert statuses["JFS-3 disconfirming recruitment"] == sweep.FALSIFIED
    assert statuses["JFS-4 disconfirming reorganization"] == sweep.FALSIFIED
    assert statuses["JFS-5 operational fixed point"] == sweep.FALSIFIED
    assert sweep.overall_status(results) == "FALSIFIED_BY_TRACE"


def test_missing_phases_are_insufficient_evidence_not_failure():
    results = sweep.evaluate_hypothesis([obs("BROAD_SCAN", {"x": 1.0})])
    assert sweep.overall_status(results) == sweep.INSUFFICIENT_EVIDENCE
    assert any(result.status == sweep.INSUFFICIENT_EVIDENCE for result in results)


def test_operational_fixed_point_does_not_require_tau_convergence():
    trace = consistent_trace()
    trace[-2] = obs(
        "CANDIDATE_SET", {"goal": 0.45, "counter": 0.35, "alt": 0.20}, tau=0.60
    )
    trace[-1] = obs(
        "CANDIDATE_SET", {"goal": 0.46, "counter": 0.34, "alt": 0.20}, tau=0.82
    )
    results = sweep.evaluate_hypothesis(trace)
    fixed_point = next(
        result for result in results if result.criterion == "JFS-5 operational fixed point"
    )
    spectral = next(
        result for result in results if result.criterion == "JFS-6 P10 spectral coupling"
    )
    assert fixed_point.status == sweep.CONSISTENT
    assert spectral.status == sweep.INSUFFICIENT_EVIDENCE


def test_goldilocks_coupling_can_be_falsified_independently():
    trace = consistent_trace()
    trace[-1] = obs(
        "CANDIDATE_SET", {"goal": 0.46, "counter": 0.34, "alt": 0.20}, tau=0.95
    )
    results = sweep.evaluate_hypothesis(trace, goldilocks=(0.55, 0.85))
    fixed_point = next(
        result for result in results if result.criterion == "JFS-5 operational fixed point"
    )
    spectral = next(
        result for result in results if result.criterion == "JFS-6 P10 spectral coupling"
    )
    assert fixed_point.status == sweep.CONSISTENT
    assert spectral.status == sweep.FALSIFIED
    assert sweep.overall_status(results) == "FALSIFIED_BY_TRACE"


def test_turnover_is_symmetric_and_bounded():
    a = {"a": 0.8, "b": 0.2}
    b = {"a": 0.2, "c": 0.8}
    ab = sweep.workspace_turnover(a, b)
    ba = sweep.workspace_turnover(b, a)
    assert ab == pytest.approx(ba)
    assert 0.0 <= ab <= 1.0


def test_rejects_negative_or_over_capacity_workspace():
    with pytest.raises(ValueError, match="non-negative"):
        sweep.normalize_workspace({"bad": -0.1})
    with pytest.raises(ValueError, match="exceeds configured capacity"):
        sweep.normalize_workspace({"a": 1, "b": 1, "c": 1}, max_capacity=2)


def test_unknown_phase_is_rejected():
    with pytest.raises(ValueError, match="unknown phase"):
        sweep.measure_trace([obs("MAGIC", {"x": 1.0})])


def test_turnover_never_leaks_between_trace_ids():
    trace = [
        obs("BROAD_SCAN", {"a": 1.0}, trace_id="a"),
        obs("BROAD_SCAN", {"b": 1.0}, trace_id="b"),
        obs("TARGET_LOCK", {"goal": 1.0}, trace_id="a"),
        obs("TARGET_LOCK", {"goal": 1.0}, trace_id="b"),
    ]
    metrics = sweep.measure_trace(trace)
    assert metrics[0].turnover is None
    assert metrics[1].turnover is None
    assert metrics[2].turnover == pytest.approx(1.0)
    assert metrics[3].turnover == pytest.approx(1.0)


def test_candidate_stability_uses_only_repeated_candidate_readouts_per_trace():
    trace = [
        obs("UNCERTAINTY_MAP", {"x": 1.0}, trace_id="a"),
        obs("CANDIDATE_SET", {"goal": 1.0}, trace_id="a"),
        obs("UNCERTAINTY_MAP", {"y": 1.0}, trace_id="b"),
        obs("CANDIDATE_SET", {"counter": 1.0}, trace_id="b"),
    ]
    results = sweep.evaluate_hypothesis(trace)
    fixed_point = next(
        result for result in results if result.criterion == "JFS-5 operational fixed point"
    )
    assert fixed_point.status == sweep.INSUFFICIENT_EVIDENCE


def test_pre_registered_thresholds_can_change_falsification_outcome():
    trace = consistent_trace()
    normal = sweep.evaluate_hypothesis(trace)
    strict = sweep.evaluate_hypothesis(trace, min_target_gain=0.90)
    normal_target = next(
        result for result in normal if result.criterion == "JFS-1 target alignment"
    )
    strict_target = next(
        result for result in strict if result.criterion == "JFS-1 target alignment"
    )
    assert normal_target.status == sweep.CONSISTENT
    assert strict_target.status == sweep.FALSIFIED


def test_phase_gains_require_paired_measurements_from_same_trace():
    trace = [
        obs("BROAD_SCAN", {"goal": 0.1, "x": 0.9}, trace_id="broad-only"),
        obs("TARGET_LOCK", {"goal": 1.0}, trace_id="lock-only"),
    ]
    results = sweep.evaluate_hypothesis(trace)
    target = next(
        result for result in results if result.criterion == "JFS-1 target alignment"
    )
    concentration_result = next(
        result for result in results if result.criterion == "JFS-2 workspace concentration"
    )
    assert target.status == sweep.INSUFFICIENT_EVIDENCE
    assert concentration_result.status == sweep.INSUFFICIENT_EVIDENCE


def test_each_trace_has_equal_weight_in_paired_gain():
    trace = [
        obs("BROAD_SCAN", {"goal": 0.1, "x": 0.9}, trace_id="a"),
        obs("TARGET_LOCK", {"goal": 0.3, "x": 0.7}, trace_id="a"),
        obs("BROAD_SCAN", {"goal": 0.8, "x": 0.2}, trace_id="b"),
        obs("TARGET_LOCK", {"goal": 0.8, "x": 0.2}, trace_id="b"),
        obs("TARGET_LOCK", {"goal": 0.8, "x": 0.2}, trace_id="b"),
        obs("TARGET_LOCK", {"goal": 0.8, "x": 0.2}, trace_id="b"),
    ]
    results = sweep.evaluate_hypothesis(trace, min_target_gain=0.09)
    target = next(
        result for result in results if result.criterion == "JFS-1 target alignment"
    )
    assert target.observed == pytest.approx(0.10)
    assert target.status == sweep.CONSISTENT


def test_spectral_coupling_refuses_partial_tau_coverage():
    trace = consistent_trace()
    trace[-1] = obs(
        "CANDIDATE_SET",
        {"goal": 0.46, "counter": 0.34, "alt": 0.20},
        tau=None,
    )
    results = sweep.evaluate_hypothesis(trace, goldilocks=(0.55, 0.85))
    spectral = next(
        result for result in results if result.criterion == "JFS-6 P10 spectral coupling"
    )
    assert spectral.status == sweep.INSUFFICIENT_EVIDENCE


def test_spectral_fraction_threshold_is_preregisterable():
    trace = consistent_trace()
    trace[-1] = obs(
        "CANDIDATE_SET", {"goal": 0.46, "counter": 0.34, "alt": 0.20}, tau=0.95
    )
    strict = sweep.evaluate_hypothesis(trace, goldilocks=(0.55, 0.85))
    permissive = sweep.evaluate_hypothesis(
        trace,
        goldilocks=(0.55, 0.85),
        min_candidate_tau_fraction=0.50,
    )
    strict_spectral = next(
        result for result in strict if result.criterion == "JFS-6 P10 spectral coupling"
    )
    permissive_spectral = next(
        result
        for result in permissive
        if result.criterion == "JFS-6 P10 spectral coupling"
    )
    assert strict_spectral.status == sweep.FALSIFIED
    assert permissive_spectral.status == sweep.CONSISTENT
