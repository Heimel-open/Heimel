from __future__ import annotations

from datetime import datetime

from .models import (
    GovernedPresentationEnvelopeV1,
    SurfaceConformanceObservationV1,
    SurfaceConformanceReportV1,
)


def evaluate_surface_conformance(observation: SurfaceConformanceObservationV1, *, presentation: GovernedPresentationEnvelopeV1 | None = None, moment: datetime | None = None) -> SurfaceConformanceReportV1:
    findings: list[str] = []
    checks = (
        (observation.owns_authoritative_state, "SHADOW_KERNEL_STATE_OWNER"),
        (observation.writes_world_state_directly, "DIRECT_WORLD_STATE_WRITE"),
        (observation.creates_authority, "AUTHORITY_CREATION_OUTSIDE_OWNER"),
        (observation.issues_clearance, "CLEARANCE_OUTSIDE_REHT"),
        (observation.promotes_inference_to_confirmed, "INFERENCE_PROMOTED_TO_CONFIRMED"),
        (observation.overrides_kernel_conflict, "KERNEL_CONFLICT_OVERRIDDEN"),
        (observation.executes_without_fresh_kernel_context, "EXECUTION_WITHOUT_FRESH_KERNEL_CONTEXT"),
    )
    findings.extend(reason for enabled, reason in checks if enabled)
    if observation.external_effect_claimed and not observation.receipt_refs:
        findings.append("EFFECT_CLAIM_WITHOUT_RECEIPT")
    if presentation is not None:
        if presentation.surface_id != observation.surface_id:
            findings.append("PRESENTATION_SURFACE_MISMATCH")
        if observation.used_for_execution:
            if observation.current_kernel_state_root is None:
                findings.append("MISSING_CURRENT_KERNEL_STATE_ROOT")
            elif observation.current_kernel_state_root != presentation.source_state_root:
                findings.append("SOURCE_STATE_ROOT_MISMATCH")
            if moment is None:
                findings.append("MISSING_EXECUTION_TIME_FOR_FRESHNESS")
            elif not presentation.is_fresh(moment):
                findings.append("STALE_PROJECTION_FOR_EXECUTION")
    elif observation.used_for_execution:
        findings.append("MISSING_GOVERNED_PRESENTATION_CONTEXT")
    ordered = tuple(dict.fromkeys(findings))
    report = SurfaceConformanceReportV1(surface_id=observation.surface_id, passed=not ordered, findings=ordered)
    return report.model_copy(update={"report_digest": report.computed_digest})
