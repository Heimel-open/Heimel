"""VAIG sustainability evidence-quality evaluation.

Build order #1492, Slice 5. Evaluates whether evidence quality is sufficient
for a sustainability datapoint/claim. Missing critical source cannot pass.
"""

from __future__ import annotations

from collections.abc import Sequence

from .quality_states import EvidenceQualityState


class EvidenceQualityEvaluator:
    """Deterministic evidence-quality assessment (no COMPLIANT output)."""

    def evaluate(
        self,
        *,
        has_source: bool,
        has_source_digest: bool,
        missing_critical_sources: Sequence[str],
        conflicts: Sequence[str],
        has_method: bool,
        has_owner: bool,
    ) -> EvidenceQualityState:
        if missing_critical_sources:
            return EvidenceQualityState.INSUFFICIENT
        if conflicts:
            return EvidenceQualityState.CONFLICTING
        if not has_source or not has_source_digest:
            return EvidenceQualityState.UNDERDETERMINED
        if not has_method or not has_owner:
            return EvidenceQualityState.CONSTRAINED
        return EvidenceQualityState.SUFFICIENT

    def can_pass_gate(self, state: EvidenceQualityState) -> bool:
        """Only SUFFICIENT passes the evidence gate; never COMPLIANT."""
        return state == EvidenceQualityState.SUFFICIENT


__all__ = ["EvidenceQualityEvaluator"]
