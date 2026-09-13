"""Provider-neutral policy-adaptive safety classifier instrument."""

import math
from typing import Optional, Callable

from vaig.instruments.base import InstrumentBase
from vaig.instruments.registry import register


@register("policy_safety_classifier", "external-policy-safety", priority=1)
class PolicySafetyClassifier(InstrumentBase):
    """Consume a bound external classifier observation as risk evidence."""

    version = "1.0.0"
    required_native_inputs = (
        "unsafe_probability",
        "classifier_id",
        "policy_id",
        "observation_digest",
    )

    def score(
        self,
        prompt: str,
        response: str,
        generate_fn: Optional[Callable[[str], str]] = None,
        judge_fn: Optional[Callable[[str], str]] = None,
        *,
        unsafe_probability: float,
        classifier_id: str,
        policy_id: str,
        observation_digest: str,
    ) -> float:
        del prompt, response, generate_fn, judge_fn
        probability = float(unsafe_probability)
        if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
            raise ValueError("unsafe_probability must be finite and in [0, 1]")
        if not classifier_id.strip():
            raise ValueError("classifier_id is required")
        if not policy_id.strip():
            raise ValueError("policy_id is required")
        if not observation_digest.startswith("sha256:") or len(observation_digest) != 71:
            raise ValueError("observation_digest must be a sha256 binding")
        return probability
