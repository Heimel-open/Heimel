"""VAIG greenwashing-risk evaluation.

Build order #1492, Slice 5. Binds greenwashing risk to concrete claims and
sources. A claim marked 'CSRD certified' without required external assurance
is high risk.
"""

from __future__ import annotations

from .quality_states import GreenwashingRisk


class GreenwashingRiskEvaluator:
    """Deterministic greenwashing-risk assessment."""

    def evaluate(
        self,
        *,
        claims_compliance: bool,   # e.g. "CSRD certified" without assurance
        has_external_assurance: bool,
        source_backs_claim: bool,
    ) -> GreenwashingRisk:
        if claims_compliance and not has_external_assurance:
            return GreenwashingRisk.HIGH
        if not source_backs_claim:
            return GreenwashingRisk.MEDIUM
        if claims_compliance and has_external_assurance:
            return GreenwashingRisk.MEDIUM
        return GreenwashingRisk.LOW


__all__ = ["GreenwashingRiskEvaluator"]
