"""Provider-neutral activation-level safety classifier evidence instrument."""

import math
from typing import Callable, Optional

from vaig.instruments.base import InstrumentBase
from vaig.instruments.registry import register


@register("activation_safety_classifier", "external-activation-safety", priority=1)
class ActivationSafetyClassifier(InstrumentBase):
    """Consume a calibrated hidden-state classifier observation as risk evidence."""

    version = "1.0.0"
    required_native_inputs = (
        "activation_unsafe_probability",
        "activation_classifier_id",
        "activation_calibration_id",
        "activation_observation_digest",
    )

    def score(
        self,
        prompt: str,
        response: str,
        generate_fn: Optional[Callable[[str], str]] = None,
        judge_fn: Optional[Callable[[str], str]] = None,
        *,
        activation_unsafe_probability: float,
        activation_classifier_id: str,
        activation_calibration_id: str,
        activation_observation_digest: str,
    ) -> float:
        del prompt, response, generate_fn, judge_fn
        probability = float(activation_unsafe_probability)
        if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
            raise ValueError("activation_unsafe_probability must be finite and in [0, 1]")
        if not activation_classifier_id.strip():
            raise ValueError("activation_classifier_id is required")
        if not activation_calibration_id.strip():
            raise ValueError("activation_calibration_id is required")
        if (
            not activation_observation_digest.startswith("sha256:")
            or len(activation_observation_digest) != 71
        ):
            raise ValueError("activation_observation_digest must be a sha256 binding")
        return probability
