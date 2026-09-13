"""Instrument: activation_probe.

White-box geometric drift measurement for supported local models. A score is
valid only when exact hidden states and a versioned calibration artifact are
bound to the instrument instance.
"""

import math
from typing import Callable, List, Optional, Sequence

from vaig.instruments.registry import register
from vaig.instruments.base import InstrumentBase


@register("activation_probe", "none", priority=0)
class NullActivationProbe(InstrumentBase):
    """Inactive placeholder for API-only deployments."""

    requires_generate_fn = False
    version = "inactive-v1"

    def score(
        self,
        prompt: str,
        response: str,
        generate_fn: Optional[Callable[[str], str]] = None,
        hidden_states: Optional[Sequence[Sequence[float]]] = None,
    ) -> float:
        raise ValueError("activation probe is unavailable for this deployment")


@register("activation_probe", "geometric_drift", priority=2)
class GeometricDriftProbe(InstrumentBase):
    """Calibrated geometric drift over local-model hidden states."""

    requires_generate_fn = False
    required_native_inputs = ("hidden_states",)
    requires_calibration = True
    version = "geometric-drift-v1"

    @classmethod
    def is_available(cls) -> bool:
        try:
            import numpy  # noqa: F401
            return True
        except ImportError:
            return False

    def __init__(
        self,
        reference_centroid: Optional[List[float]] = None,
        calibration_profile: Optional[str] = None,
        normalization_scale: Optional[float] = None,
    ):
        self.reference_centroid = (
            tuple(float(value) for value in reference_centroid)
            if reference_centroid is not None else None
        )
        self.calibration_profile = calibration_profile
        self.normalization_scale = (
            float(normalization_scale)
            if normalization_scale is not None else None
        )

    def is_calibrated(self) -> bool:
        return bool(
            self.reference_centroid
            and self.calibration_profile
            and self.normalization_scale is not None
            and self.normalization_scale > 0.0
        )

    def calibration_profile_id(self) -> Optional[str]:
        return self.calibration_profile if self.is_calibrated() else None

    def score(
        self,
        prompt: str,
        response: str,
        generate_fn: Optional[Callable[[str], str]] = None,
        hidden_states: Optional[Sequence[Sequence[float]]] = None,
    ) -> float:
        if not self.is_calibrated():
            raise ValueError("versioned activation calibration is required")
        if hidden_states is None or len(hidden_states) == 0:
            raise ValueError("hidden states are required")

        centroid = self.reference_centroid
        if centroid is None or self.normalization_scale is None:
            raise ValueError("activation calibration is incomplete")

        width = len(centroid)
        drifts = []
        for state in hidden_states:
            values = tuple(float(value) for value in state)
            if len(values) != width:
                raise ValueError("hidden-state dimension does not match calibration centroid")
            if any(not math.isfinite(value) for value in values):
                raise ValueError("hidden states must contain finite values")
            distance = math.sqrt(
                sum((value - reference) ** 2 for value, reference in zip(values, centroid))
            )
            drifts.append(distance)

        mean_drift = sum(drifts) / len(drifts)
        return min(mean_drift / self.normalization_scale, 1.0)
