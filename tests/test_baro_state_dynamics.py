"""
Tests — BARO State Dynamics Monitor (#428, experimental/shadow hardening).

Covers: uneven intervals, noisy signal, movement away from nearest but toward
opposite boundary, value already out of bounds, extremely small intervals,
falling signal toward lower bound, missing/invalid data. Plus experimental-mode
marking, confidence model, and bounds validation.
"""

from src.valo_platform.baro_state_dynamics import (
    StateDynamicsMonitor,
    RealityPackage,
    SamplePoint,
    StateTrend,
    TrendDirection,
    ProjectionType,
)


def rp(unit="percent", source="test-sensor", cadence=1.0, window=10.0):
    return RealityPackage(unit=unit, source=source,
                           sampling_cadence=cadence, observation_window=window)


def obs(*vals, times=None, stds=None, lower=-100.0, upper=100.0,
       unit="percent", source="test-sensor", cadence=1.0, window=None):
    if times is None:
        times = list(range(len(vals)))
    if window is None:
        window = (times[-1] - times[0]) if len(times) > 1 else 1.0
    samples = [
        SamplePoint(value=v, time=t, value_std=(stds[i] if stds else None))
        for i, (v, t) in enumerate(zip(vals, times))
    ]
    m = StateDynamicsMonitor(boundary_lower=lower, boundary_upper=upper,
                             unit=unit, source=source)
    return m, m.observe_window(samples, rp(unit, source, cadence, window))


# --- experimental / shadow mode ------------------------------------------

def test_mode_is_experimental_shadow():
    m, o = obs(10, 20, 30)
    assert o.mode == "experimental_shadow"
    assert "experimental" in o.estimator_version


def test_projection_marked_linear_extrapolation_not_expected_breach():
    m, o = obs(10, 20, 30, 40, 45, lower=0.0, upper=100.0)
    if o.projected_breach_seconds is not None:
        assert o.projection_type == ProjectionType.LINEAR_EXTRAPOLATION.value
        assert o.projection_type != "expected_breach"


# --- scenario 1: uneven time intervals ------------------------------------

def test_uneven_intervals_still_produces_velocity():
    m, o = obs(0.0, 1.0, 2.2, 1.5, times=[0, 1.0, 3.5, 4.0], cadence=1.0, window=4.0)
    assert o.velocity is not None
    assert o.confidence_model is not None
    assert o.confidence_model.sampling_regularity < 1.0


# --- scenario 2: noisy signal ----------------------------------------------

def test_noisy_signal_velocity_reliable_but_noise_flagged():
    vals = [0.0, 1.1, 0.9, 2.2, 1.8, 3.0]
    stds = [0.4, 0.4, 0.4, 0.4, 0.4, 0.4]
    m, o = obs(*vals, stds=stds, cadence=1.0, window=6.0)
    assert o.velocity is not None
    assert o.velocity_reliable is True
    assert o.confidence_model is not None
    assert o.confidence_model.noise > 0.0


# --- scenario 3: moving away from nearest, toward opposite boundary -------

def test_near_upper_but_falling_targets_lower():
    m, o = obs(95.0, 92.0, 89.0, lower=0.0, upper=100.0, cadence=1.0, window=3.0)
    assert o.velocity < 0
    assert o.boundary_direction == TrendDirection.TOWARD_LOWER.value
    # distance to lower (~89) is large; nearest (upper) would be ~11
    assert o.boundary_distance is not None
    assert o.boundary_distance > 50.0


def test_rising_targets_upper_not_nearest():
    m, o = obs(5.0, 8.0, 11.0, lower=0.0, upper=100.0, cadence=1.0, window=3.0)
    assert o.velocity > 0
    assert o.boundary_direction == TrendDirection.TOWARD_UPPER.value
    assert o.boundary_distance is not None
    # current (11) is near LOWER; rising toward UPPER (100) -> distance is large
    assert o.boundary_distance > 50.0


# --- scenario 4: value already outside bounds -----------------------------

def test_value_already_out_of_bounds_is_breached_not_crash():
    m, o = obs(150.0, 151.0, 152.0, lower=0.0, upper=100.0, cadence=1.0, window=3.0)
    assert o.trend == StateTrend.BREACHED
    assert o.rejected is False
    assert o.boundary_distance == 0.0


# --- scenario 5: extremely small time intervals ---------------------------

def test_extremely_small_intervals_handled():
    m, o = obs(0.0, 0.1, 0.2, 0.15, times=[0.0, 1e-6, 2e-6, 3e-6],
               cadence=1e-6, window=3e-6)
    assert o.velocity is not None
    assert o.confidence_model is not None
    assert o.confidence_model.timestamp_precision <= 0.3


# --- scenario 6: falling signal toward lower bound ------------------------

def test_falling_toward_lower_bound_projection():
    m, o = obs(40.0, 35.0, 30.0, 25.0, 20.0, lower=0.0, upper=100.0,
               cadence=1.0, window=5.0)
    assert o.velocity < 0
    assert o.boundary_direction == TrendDirection.TOWARD_LOWER.value
    if o.projected_breach_seconds is not None:
        assert o.projection_type == ProjectionType.LINEAR_EXTRAPOLATION.value


# --- scenario 7: missing and invalid data ---------------------------------

def test_invalid_sample_value_rejected():
    samples = [SamplePoint(value=float('nan'), time=0.0),
               SamplePoint(value=1.0, time=1.0)]
    m = StateDynamicsMonitor(boundary_lower=0.0, boundary_upper=100.0,
                             unit="percent", source="s")
    o = m.observe_window(samples, rp())
    assert o.rejected is True
    assert o.rejection_reason == "invalid_sample_value"


def test_missing_points_counted_in_confidence():
    m, o = obs(0.0, 1.0, 2.0, times=[0.0, 1.0, 6.0], cadence=1.0, window=6.0)
    assert o.confidence_model is not None
    assert o.confidence_model.missing_points >= 1


# --- bounds validation -----------------------------------------------------

def test_lower_greater_equal_upper_rejected():
    m = StateDynamicsMonitor(boundary_lower=100.0, boundary_upper=0.0,
                              unit="percent", source="s")
    assert m.validate_bounds() == "lower_greater_or_equal_upper"
    o = m.observe_window([SamplePoint(50.0, 0.0)], rp())
    assert o.rejected is True
    assert o.rejection_reason == "lower_greater_or_equal_upper"


def test_unknown_unit_rejected():
    m = StateDynamicsMonitor(boundary_lower=0.0, boundary_upper=100.0,
                             unit="", source="s")
    assert m.validate_bounds() == "unknown_unit"
    o = m.observe_window([SamplePoint(50.0, 0.0)], rp(unit=""))
    assert o.rejected is True


def test_unit_mismatch_rejected():
    m = StateDynamicsMonitor(boundary_lower=0.0, boundary_upper=100.0,
                             unit="percent", source="s")
    o = m.observe_window([SamplePoint(50.0, 0.0)], rp(unit="celsius"))
    assert o.rejected is True
    assert o.rejection_reason == "unit_mismatch"


# --- confidence model structure -------------------------------------------

def test_confidence_is_model_not_scalar():
    m, o = obs(10.0, 20.0, 30.0, 40.0, 50.0, cadence=1.0, window=5.0)
    cm = o.confidence_model
    assert cm is not None
    for attr in ("coverage", "sampling_regularity", "missing_points",
                 "noise", "variance", "timestamp_precision", "combined"):
        assert hasattr(cm, attr)
    assert 0.0 <= cm.combined <= 1.0


def test_weak_data_marks_derivatives_unreliable():
    m, o = obs(1.0, 2.0, cadence=1.0, window=2.0)
    assert o.velocity_reliable is True
    assert o.acceleration_reliable is False
    assert o.jerk_reliable is False
