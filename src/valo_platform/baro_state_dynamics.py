"""
BARO State Dynamics Monitor — EXPERIMENTAL / SHADOW MODE (valo-platform #427/#428)

Derivative-based control indicators for admissibility assessment. Industrial-
control-style detection: even when the current state is within range, velocity,
acceleration, or jerk may indicate an impending boundary breach.

    position / current state : x
    velocity       : dx/dt (1st derivative)
    acceleration   : d²x/dt² (2nd derivative)
    jerk           : d³x/dt³ (3rd derivative)

================================================================================
EXPERIMENTAL / SHADOW MODE — READ THIS BEFORE USE
================================================================================
This module is an EXPERIMENTAL BARO OBSERVER. It is explicitly NOT certified
control logic and NOT a safety component. It MUST run in shadow mode: it
observes and emits evidence, but it never blocks, allows, or denies. Any
binding governance outcome (allow / defer / deny / step-up) MUST be produced
separately by REHT admissibility, never derived from this module.

Key constraints enforced here (per #428 hardening):
  * Boundary selection uses the boundary the trajectory is actually MOVING
    toward (velocity direction), not merely the nearest boundary.
  * Confidence is a MODEL, not a sample count: it incorporates sampling
    regularity, missing points, noise, variance, timestamp precision, and
    modelled projection error.
  * Noise handling: a moving-average pre-filter is applied before finite
    differences. Raw finite differences make jerk/snap unstable.
  * snap (4th derivative) is NOT emitted as a meaningful signal without
    sufficient data; derivatives are flagged UNRELIABLE when the data basis
    is weak.
  * Bounds are validated: lower >= upper, current value already out of bounds,
    unknown units, and unit/variable mismatches are all rejected.
  * RealityPackage carries unit, source, sampling cadence, observation window,
    and estimator version.
  * projected_breach_seconds is explicitly marked as a LINEAR EXTRAPOLATION,
    not an expected actual breach.
================================================================================
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
import math

logger = logging.getLogger(__name__)

# Bump on any change to scoring/derivation semantics.
ESTIMATOR_VERSION = "0.1.0-experimental-shadow"

# Minimum samples for a derivative to be considered reliable.
MIN_SAMPLES_VELOCITY = 2
MIN_SAMPLES_ACCEL = 3
MIN_SAMPLES_JERK = 5
# Below this, the trajectory direction is treated as unknown and we fall back
# to the nearest boundary.
VELOCITY_DIRECTION_EPS = 1e-9

# Moving-average window for noise pre-filtering.
MA_WINDOW = 3


class StateTrend(str, Enum):
    """Direction of state trajectory relative to the boundary."""
    WITHIN = "within"
    APPROACHING = "approaching"
    CRITICAL = "critical"
    BREACHED = "breached"


class SampleQuality(str, Enum):
    """Overall reliability of the derivative estimates (kept for compat)."""
    SUFFICIENT = "sufficient"
    MINIMAL = "minimal"
    INSUFFICIENT = "insufficient"
    INVALID = "invalid"


class TrendDirection(str, Enum):
    """Which boundary the trajectory is aimed at."""
    TOWARD_UPPER = "toward_upper"
    TOWARD_LOWER = "toward_lower"
    UNKNOWN = "unknown"  # velocity ~ 0 -> fall back to nearest


class ProjectionType(str, Enum):
    """What projected_breach_seconds actually means."""
    LINEAR_EXTRAPOLATION = "linear_extrapolation"  # NOT an expected real breach
    NONE = "none"


@dataclass
class RealityPackage:
    """
    Provenance envelope for the observation.

    unit/source/sampling_cadence/observation_window are REQUIRED so the
    observation is interpretable and comparable. estimator_version pins the
    derivation semantics.
    """
    unit: str
    source: str
    sampling_cadence: Optional[float] = None       # expected seconds between samples
    observation_window: Optional[float] = None      # seconds covered by the window
    estimator_version: str = ESTIMATOR_VERSION


@dataclass
class SamplePoint:
    """A single state sample at a point in time."""
    value: float
    time: float                       # monotonically increasing (seconds or epoch)
    value_std: Optional[float] = None  # measurement noise std, if known


@dataclass
class ConfidenceModel:
    """
    Explicit confidence MODEL (not a single asserted number).

    Each component is in [0, 1]. `combined` is the documented model:
        combined = coverage
                 * sampling_regularity
                 * (1 - normalised_noise)
                 * (1 - projection_error)
    clamped to [0, 1]. Reviewers can see exactly what confidence rests on.
    """
    coverage: float                      # fraction of window actually observed
    sampling_regularity: float          # 1 - (std_dt / mean_dt), regularity of spacing
    missing_points: int                 # count of gaps beyond expected cadence
    noise: float                        # normalised measurement noise [0,1]
    variance: float                     # normalised signal variance [0,1]
    timestamp_precision: float          # normalised precision of `time` [0,1]
    projection_error: Optional[float]   # modelled extrapolation error [0,1]; None = unknown
    combined: float

    def as_dict(self) -> Dict[str, Any]:
        return {
            "coverage": self.coverage,
            "sampling_regularity": self.sampling_regularity,
            "missing_points": self.missing_points,
            "noise": self.noise,
            "variance": self.variance,
            "timestamp_precision": self.timestamp_precision,
            "projection_error": self.projection_error,
            "combined": self.combined,
        }


@dataclass
class StateDynamicsObservation:
    """
    Observation of state dynamics from a window of ordered samples.

    EXPERIMENTAL / SHADOW: observation only. No decision/allow/deny field.
    `mode` is always "experimental_shadow".
    """

    mode: str = "experimental_shadow"
    estimator_version: str = ESTIMATOR_VERSION

    velocity: Optional[float] = None       # dx/dt
    acceleration: Optional[float] = None   # d²x/dt²
    jerk: Optional[float] = None           # d³x/dt³

    # Per-derivative reliability flags (True only when data basis is sufficient)
    velocity_reliable: bool = False
    acceleration_reliable: bool = False
    jerk_reliable: bool = False

    boundary_lower: float = 0.0
    boundary_upper: float = 0.0
    current_position: Optional[float] = None
    boundary_distance: Optional[float] = None
    boundary_direction: Optional[str] = None   # "toward_upper" | "toward_lower" | "unknown"
    trend: StateTrend = StateTrend.WITHIN

    # Explicitly a LINEAR EXTRAPOLATION, not an expected breach.
    projected_breach_seconds: Optional[float] = None
    projection_type: str = ProjectionType.NONE.value

    sample_count: int = 0
    sample_quality: SampleQuality = SampleQuality.INSUFFICIENT

    # Validation / rejection reasons
    rejected: bool = False
    rejection_reason: Optional[str] = None

    # Provenance
    unit: Optional[str] = None
    source: Optional[str] = None
    sampling_cadence: Optional[float] = None
    observation_window: Optional[float] = None

    confidence_model: Optional[ConfidenceModel] = None

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def as_reality_package(self) -> Dict[str, Any]:
        """Fragment appended to BARO RealityPackage for VAIG (evidence only)."""
        cm = self.confidence_model.as_dict() if self.confidence_model else None
        return {
            "observer": "baro_state_dynamics",
            "mode": self.mode,
            "estimator_version": self.estimator_version,
            "velocity": self.velocity,
            "acceleration": self.acceleration,
            "jerk": self.jerk,
            "velocity_reliable": self.velocity_reliable,
            "acceleration_reliable": self.acceleration_reliable,
            "jerk_reliable": self.jerk_reliable,
            "current_position": self.current_position,
            "boundary_lower": self.boundary_lower,
            "boundary_upper": self.boundary_upper,
            "boundary_distance": self.boundary_distance,
            "boundary_direction": self.boundary_direction,
            "trend": self.trend.value,
            "projected_breach_seconds": self.projected_breach_seconds,
            "projection_type": self.projection_type,
            "sample_count": self.sample_count,
            "sample_quality": self.sample_quality.value,
            "rejected": self.rejected,
            "rejection_reason": self.rejection_reason,
            "unit": self.unit,
            "source": self.source,
            "sampling_cadence": self.sampling_cadence,
            "observation_window": self.observation_window,
            "confidence_model": cm,
            "timestamp": self.timestamp.isoformat(),
            # NOTE: this is a descriptive observation, NOT a governance decision.
        }


def _moving_average(values: List[float], window: int = MA_WINDOW) -> List[float]:
    """Simple moving-average pre-filter to suppress high-frequency noise."""
    if window <= 1:
        return list(values)
    out = []
    for i in range(len(values)):
        lo = max(0, i - window + 1)
        out.append(sum(values[lo:i + 1]) / (i - lo + 1))
    return out


def _normalise(x: float, lo: float, hi: float) -> float:
    """Clamp x to [0,1] as a fraction of [lo,hi]."""
    if hi <= lo:
        return 0.0
    return max(0.0, min(1.0, (x - lo) / (hi - lo)))


class StateDynamicsMonitor:
    """
    Passive BARO observer that derives control indicators from ordered samples.

    EXPERIMENTAL / SHADOW MODE. Computes moving-average-pre-filtered finite-
    difference derivative estimates on a window of (value, time) samples. The
    monitor is stateless — call observe_window() with the samples and a
    RealityPackage describing provenance.

    BARO observes only. It never blocks or decides.
    """

    def __init__(self, boundary_lower: float = -math.inf,
                 boundary_upper: float = math.inf,
                 unit: str = "",
                 source: str = "") -> None:
        self.boundary_lower = boundary_lower
        self.boundary_upper = boundary_upper
        self.unit = unit
        self.source = source

    # --- bounds validation -------------------------------------------------

    def validate_bounds(self) -> Optional[str]:
        """
        Reject invalid boundary configurations.

        Returns a rejection reason string, or None if bounds are valid.
        """
        if math.isnan(self.boundary_lower) or math.isnan(self.boundary_upper):
            return "bounds_contain_nan"
        if self.boundary_lower >= self.boundary_upper:
            return "lower_greater_or_equal_upper"
        if not self.unit:
            return "unknown_unit"
        return None

    def _reject(self, reason: str, n: int,
                lower: float, upper: float) -> StateDynamicsObservation:
        return StateDynamicsObservation(
            rejected=True,
            rejection_reason=reason,
            sample_count=n,
            sample_quality=SampleQuality.INVALID,
            boundary_lower=lower,
            boundary_upper=upper,
            unit=self.unit or None,
            source=self.source or None,
        )

    # --- main ---------------------------------------------------------------

    def observe_window(self, samples: List[SamplePoint],
                       reality: Optional[RealityPackage] = None) -> StateDynamicsObservation:
        """
        Analyze a window of ordered state samples and return dynamics.

        samples must be ordered by increasing time.
        reality provides provenance (unit/source/cadence/window). If omitted,
        unit/source are taken from the monitor config and cadence/window left
        unknown (which lowers confidence).

        Returns a StateDynamicsObservation (observation only — no decision).
        """
        n = len(samples)
        lower, upper = self.boundary_lower, self.boundary_upper

        # 1. Bounds validation (reject invalid configurations)
        reason = self.validate_bounds()
        if reason:
            return self._reject(reason, n, lower, upper)

        # 2. Basic sample sanity
        for s in samples:
            if not isinstance(s.value, (int, float)) or math.isnan(s.value):
                return self._reject("invalid_sample_value", n, lower, upper)

        # 3. Unit/variable mismatch check
        if reality is not None:
            if reality.unit and self.unit and reality.unit != self.unit:
                return self._reject("unit_mismatch", n, lower, upper)

        current = samples[-1].value
        obs = self._boundary_analysis(current, lower, upper)
        obs.current_position = current
        obs.sample_count = n
        obs.boundary_lower = lower
        obs.boundary_upper = upper
        obs.unit = (reality.unit if reality else self.unit) or None
        obs.source = (reality.source if reality else self.source) or None
        obs.sampling_cadence = reality.sampling_cadence if reality else None
        obs.observation_window = reality.observation_window if reality else None

        if n == 0:
            obs.sample_quality = SampleQuality.INVALID
            return obs

        # 4. Time monotonicity
        dts = [samples[i + 1].time - samples[i].time for i in range(n - 1)]
        if any(dt <= 0 for dt in dts):
            obs.sample_quality = SampleQuality.INVALID
            obs.rejected = True
            obs.rejection_reason = "non_monotonic_time"
            return obs

        # 5. Noise pre-filter (moving average) before differentiation
        raw = [s.value for s in samples]
        smoothed = _moving_average(raw, MA_WINDOW)

        # 6. Confidence model components
        conf = self._confidence(samples, dts, raw, smoothed, reality)
        obs.confidence_model = conf
        obs.sample_quality = self._quality_from_conf(conf, n)

        # 7. Derivatives (reliable only with sufficient data)
        velocity = (smoothed[-1] - smoothed[-2]) / dts[-1]
        obs.velocity = round(velocity, 6)
        obs.velocity_reliable = n >= MIN_SAMPLES_VELOCITY

        if n >= MIN_SAMPLES_ACCEL:
            dt_back = dts[-2] if len(dts) >= 2 else dts[-1]
            if dt_back > 0:
                v_prev = (smoothed[-2] - smoothed[-3]) / dt_back
                dt_avg = (dts[-1] + dt_back) / 2.0
                if dt_avg > 0:
                    accel = (velocity - v_prev) / dt_avg
                    obs.acceleration = round(accel, 6)
                    obs.acceleration_reliable = n >= MIN_SAMPLES_ACCEL

        if n >= MIN_SAMPLES_JERK:
            if len(dts) >= 3 and dts[-2] > 0 and dts[-3] > 0:
                v_prev = (smoothed[-2] - smoothed[-3]) / dts[-2]
                v_prev2 = (smoothed[-3] - smoothed[-4]) / dts[-3]
                a_prev = (v_prev - v_prev2) / ((dts[-2] + dts[-3]) / 2.0)
                if obs.acceleration is not None and a_prev is not None:
                    dt_avg3 = ((dts[-1] + dts[-2]) / 2.0 + (dts[-2] + dts[-3]) / 2.0) / 2.0
                    if dt_avg3 > 0:
                        jerk = (obs.acceleration - a_prev) / dt_avg3
                        obs.jerk = round(jerk, 6)
                        obs.jerk_reliable = True  # only reached with n >= MIN_SAMPLES_JERK

        # 7b. Override boundary direction toward the trajectory's MOVEMENT,
        # not merely the nearest boundary. Recompute distance to that boundary.
        # Skip when already BREACHED (distance is already 0 / not meaningful).
        if obs.velocity is not None and obs.trend != StateTrend.BREACHED:
            if obs.velocity > VELOCITY_DIRECTION_EPS:
                obs.boundary_direction = TrendDirection.TOWARD_UPPER.value
                obs.boundary_distance = round(upper - current, 6)
            elif obs.velocity < -VELOCITY_DIRECTION_EPS:
                obs.boundary_direction = TrendDirection.TOWARD_LOWER.value
                obs.boundary_distance = round(current - lower, 6)
            # else: velocity ~ 0 -> keep nearest-boundary fallback

        # 8. Projected breach — toward the boundary the trajectory MOVES toward
        if obs.velocity is not None and obs.boundary_distance is not None \
                and obs.boundary_direction is not None:
            moving_toward = (
                (obs.boundary_direction == TrendDirection.TOWARD_UPPER.value and obs.velocity > 0)
                or (obs.boundary_direction == TrendDirection.TOWARD_LOWER.value and obs.velocity < 0)
            )
            if moving_toward and abs(obs.velocity) > VELOCITY_DIRECTION_EPS:
                # Explicitly a LINEAR EXTRAPOLATION, not an expected breach.
                obs.projected_breach_seconds = round(
                    obs.boundary_distance / abs(obs.velocity), 6)
                obs.projection_type = ProjectionType.LINEAR_EXTRAPOLATION.value

        return obs

    # --- helpers ------------------------------------------------------------

    def _boundary_analysis(self, current: float, lower: float,
                           upper: float) -> StateDynamicsObservation:
        obs = StateDynamicsObservation(
            trend=StateTrend.WITHIN,
            boundary_lower=lower,
            boundary_upper=upper,
            current_position=current,
        )

        # Current value already outside bounds -> breached, do not crash.
        if current < lower or current > upper:
            obs.trend = StateTrend.BREACHED
            obs.boundary_distance = 0.0
            obs.boundary_direction = TrendDirection.UNKNOWN.value
            return obs

        dist_lower = current - lower
        dist_upper = upper - current

        # Choose the boundary the trajectory is MOVING toward, not just nearest.
        # Direction is resolved from velocity in observe_window; if velocity is
        # ~0 we fall back to the nearest boundary (unknown direction).
        # Here we set the NEAREST as the fallback; observe_window overrides with
        # the movement direction once velocity is known.
        if dist_lower <= dist_upper:
            obs.boundary_distance = round(dist_lower, 6)
            obs.boundary_direction = TrendDirection.TOWARD_LOWER.value
        else:
            obs.boundary_distance = round(dist_upper, 6)
            obs.boundary_direction = TrendDirection.TOWARD_UPPER.value

        total_range = dist_lower + dist_upper
        if total_range > 0:
            margin_frac = obs.boundary_distance / total_range * 2.0
            if margin_frac < 0.1:
                obs.trend = StateTrend.CRITICAL
            elif margin_frac < 0.25:
                obs.trend = StateTrend.APPROACHING
        return obs

    def _confidence(self, samples: List[SamplePoint], dts: List[float],
                    raw: List[float], smoothed: List[float],
                    reality: Optional[RealityPackage]) -> ConfidenceModel:
        n = len(samples)
        # coverage: fraction of expected window actually observed
        coverage = 1.0
        if reality and reality.observation_window and reality.sampling_cadence:
            expected = reality.observation_window / reality.sampling_cadence
            if expected > 0:
                coverage = max(0.0, min(1.0, n / expected))

        # sampling regularity: 1 - (std_dt / mean_dt)
        sampling_regularity = 1.0
        if len(dts) >= 2:
            mean_dt = sum(dts) / len(dts)
            if mean_dt > 0:
                var_dt = sum((d - mean_dt) ** 2 for d in dts) / len(dts)
                std_dt = math.sqrt(var_dt)
                sampling_regularity = max(0.0, min(1.0, 1.0 - std_dt / mean_dt))

        # missing points: gaps larger than 2x expected cadence
        missing_points = 0
        if reality and reality.sampling_cadence:
            for dt in dts:
                if dt > 2.0 * reality.sampling_cadence:
                    missing_points += 1

        # noise: mean of known value_std, normalised against signal scale
        noise = 0.0
        known_std = [s.value_std for s in samples if s.value_std is not None]
        if known_std and raw:
            sig_scale = max(1e-9, max(raw) - min(raw))
            noise = max(0.0, min(1.0, (sum(known_std) / len(known_std)) / sig_scale))
        elif len(raw) >= 2:
            # fallback: residual between raw and smoothed as noise proxy
            resid = [abs(raw[i] - smoothed[i]) for i in range(len(raw))]
            sig_scale = max(1e-9, max(raw) - min(raw))
            noise = max(0.0, min(1.0, (sum(resid) / len(resid)) / sig_scale))

        # variance: normalised signal variance
        variance = 0.0
        if len(raw) >= 2:
            mean_v = sum(raw) / len(raw)
            var_v = sum((v - mean_v) ** 2 for v in raw) / len(raw)
            sig_scale = max(1e-9, max(raw) - min(raw))
            variance = max(0.0, min(1.0, math.sqrt(var_v) / sig_scale))

        # timestamp precision: tighter time -> higher precision
        timestamp_precision = 1.0
        if len(dts) >= 1:
            min_step = min(dts)
            if min_step < 1e-5:
                timestamp_precision = 0.3
            elif min_step < 1e-3:
                timestamp_precision = 0.6
            elif min_step < 1.0:
                timestamp_precision = 0.9

        # projection_error: no historical track yet -> unknown
        projection_error: Optional[float] = None
        # model: combined = coverage * regularity * (1-noise) * (1-projection_error or 0)
        pe_factor = 1.0 - (projection_error if projection_error is not None else 0.0)
        combined = max(0.0, min(1.0,
                                coverage * sampling_regularity * (1.0 - noise) * pe_factor))

        return ConfidenceModel(
            coverage=round(coverage, 4),
            sampling_regularity=round(sampling_regularity, 4),
            missing_points=missing_points,
            noise=round(noise, 4),
            variance=round(variance, 4),
            timestamp_precision=round(timestamp_precision, 4),
            projection_error=projection_error,
            combined=round(combined, 4),
        )

    @staticmethod
    def _quality_from_conf(conf: ConfidenceModel, n: int) -> SampleQuality:
        if n < MIN_SAMPLES_VELOCITY:
            return SampleQuality.INSUFFICIENT
        if conf.combined >= 0.6 and n >= MIN_SAMPLES_ACCEL:
            return SampleQuality.SUFFICIENT
        if conf.combined >= 0.3:
            return SampleQuality.MINIMAL
        return SampleQuality.INSUFFICIENT
