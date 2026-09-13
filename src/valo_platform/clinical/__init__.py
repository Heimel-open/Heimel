"""Canonical clinical event models for shadow-only governance verticals.

This package contains domain data structures only. It must not diagnose,
recommend treatment, or become an admissibility authority.
"""

from .models import (
    ClinicalEvent,
    ClinicalEventType,
    ClinicalStateSnapshot,
    DataQualityState,
    GuardianShadowObservation,
)

__all__ = [
    "ClinicalEvent",
    "ClinicalEventType",
    "ClinicalStateSnapshot",
    "DataQualityState",
    "GuardianShadowObservation",
]
