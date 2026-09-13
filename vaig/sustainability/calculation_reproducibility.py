"""VAIG calculation-reproducibility evaluation.

Build order #1492, Slice 5. Checks whether a reported datapoint can be
reproduced from source -> calculation -> method. Changed method or factor
must invalidate prior reproducibility.
"""

from __future__ import annotations

from .quality_states import EvidenceQualityState


class CalculationReproducibility:
    """Deterministic reproducibility check for a calculated datapoint."""

    def evaluate(
        self,
        *,
        has_recipe: bool,
        has_inputs: bool,
        method_version_matches: bool,
        factors_match: bool,
    ) -> EvidenceQualityState:
        if not has_recipe or not has_inputs:
            return EvidenceQualityState.UNDERDETERMINED
        if not method_version_matches or not factors_match:
            return EvidenceQualityState.CONSTRAINED
        return EvidenceQualityState.SUFFICIENT


__all__ = ["CalculationReproducibility"]
