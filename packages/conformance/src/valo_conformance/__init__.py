"""Portable, authority-neutral cross-stack conformance contracts."""

from .evaluate import evaluate_surface_conformance
from .models import (
    GovernedPresentationClaimV1,
    GovernedPresentationEnvelopeV1,
    SurfaceConformanceObservationV1,
    SurfaceConformanceReportV1,
)

__all__ = [
    "GovernedPresentationClaimV1",
    "GovernedPresentationEnvelopeV1",
    "SurfaceConformanceObservationV1",
    "SurfaceConformanceReportV1",
    "evaluate_surface_conformance",
]
