"""VAIG sustainability evidence-quality and claim-risk evaluation.

Build order #1492, Slice 5. VAIG evaluates evidence quality, calculation
reproducibility and greenwashing/claim risk. Outputs use bounded states
(SUFFICIENT/CONSTRAINED/INSUFFICIENT/UNDERDETERMINED/CONFLICTING) — never
COMPLIANT.
"""

from .calculation_reproducibility import CalculationReproducibility
from .evidence_quality import EvidenceQualityEvaluator
from .greenwashing_risk import GreenwashingRiskEvaluator
from .quality_states import (
    ClaimSupportState,
    EvidenceQualityState,
    GreenwashingRisk,
)

__all__ = [
    "CalculationReproducibility",
    "ClaimSupportState",
    "EvidenceQualityEvaluator",
    "EvidenceQualityState",
    "GreenwashingRisk",
    "GreenwashingRiskEvaluator",
]
