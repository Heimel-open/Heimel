"""VAIG sustainability evidence-quality states.

Build order #1492, Slice 5 (VAIG). VAIG evaluates evidence quality and
claim risk. Outputs use bounded states — never COMPLIANT.
"""

from __future__ import annotations

from enum import Enum


class EvidenceQualityState(str, Enum):
    SUFFICIENT = "SUFFICIENT"
    CONSTRAINED = "CONSTRAINED"
    INSUFFICIENT = "INSUFFICIENT"
    UNDERDETERMINED = "UNDERDETERMINED"
    CONFLICTING = "CONFLICTING"


class ClaimSupportState(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    UNDERDETERMINED = "UNDERDETERMINED"
    CONFLICTING = "CONFLICTING"


class GreenwashingRisk(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    UNDETERMINED = "UNDETERMINED"


__all__ = ["ClaimSupportState", "EvidenceQualityState", "GreenwashingRisk"]
