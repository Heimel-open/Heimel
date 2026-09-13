"""Instrument: logprob_scorer.

Measures mean token surprisal from native provider log probabilities. Text
entropy is not a model-confidence measurement and is intentionally not used as
a fallback.
"""

import math
from typing import Callable, Optional, Sequence

from vaig.instruments.registry import register
from vaig.instruments.base import InstrumentBase


@register("logprob_scorer", "default")
class TokenEntropyLogprobScorer(InstrumentBase):
    """Convert native token log probabilities to a normalized risk score."""

    requires_generate_fn = False
    required_native_inputs = ("logprobs",)
    version = "native-logprob-surprisal-v1"

    # Mean token surprisal in nats. This normalization is still heuristic until
    # a domain/model calibration profile is introduced in P0.6.
    _LOW_CONFIDENCE_THRESHOLD = 3.5

    def score(
        self,
        prompt: str,
        response: str,
        generate_fn: Optional[Callable[[str], str]] = None,
        logprobs: Optional[Sequence[float]] = None,
    ) -> float:
        if logprobs is None or len(logprobs) == 0:
            raise ValueError("native logprobs are required")

        values = [float(value) for value in logprobs]
        if any(not math.isfinite(value) or value > 0.0 for value in values):
            raise ValueError("logprobs must be finite natural-log probabilities <= 0")

        mean_surprisal = -sum(values) / len(values)
        return min(mean_surprisal / self._LOW_CONFIDENCE_THRESHOLD, 1.0)
