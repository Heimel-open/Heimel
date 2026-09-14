from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class HarnessConformanceError(ValueError):
    pass


class HarnessState(str, Enum):
    KNOWN = "KNOWN"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class HarnessDescriptor:
    harness_id: str
    version: str
    config_digest: str
    provenance_ref: str
    state: HarnessState = HarnessState.KNOWN


@dataclass(frozen=True)
class HarnessAdmissionEvidence:
    incoming_harness: HarnessDescriptor
    external_harness: HarnessDescriptor
    pre_induction_assessed: bool
    controlled_regrounding_applied: bool
    residual_induction_measured: bool
    residual_induction_within_bound: bool
    equivalence_scope: str
    evidence_ref: str


@dataclass(frozen=True)
class HarnessAdmissionResult:
    admissible_for_consequence_bearing_work: bool
    reasons: tuple[str, ...]


def verify_harness_admission(
    evidence: HarnessAdmissionEvidence,
) -> HarnessAdmissionResult:
    """Evaluate whether a model/harness transition may enter consequence-bearing work.

    The external harness is never presumed to dominate the incoming/internal
    harness. Incoming operational framing is treated as prior state. Admission
    requires known harness provenance, explicit pre-induction assessment,
    controlled re-grounding, and bounded residual-induction evidence.

    UNKNOWN remains unknown: missing or opaque incoming harness state cannot be
    promoted into consequence-bearing authority merely by applying an external
    system prompt or wrapper.
    """
    reasons: list[str] = []

    for label, harness in (
        ("incoming", evidence.incoming_harness),
        ("external", evidence.external_harness),
    ):
        if harness.state is HarnessState.UNKNOWN:
            reasons.append(f"{label}_harness_unknown")
        if not harness.harness_id:
            reasons.append(f"{label}_harness_id_missing")
        if not harness.version:
            reasons.append(f"{label}_harness_version_missing")
        if not harness.config_digest.startswith("sha256:"):
            reasons.append(f"{label}_harness_config_digest_invalid")
        if not harness.provenance_ref:
            reasons.append(f"{label}_harness_provenance_missing")

    if not evidence.pre_induction_assessed:
        reasons.append("pre_induction_not_assessed")
    if not evidence.controlled_regrounding_applied:
        reasons.append("controlled_regrounding_not_applied")
    if not evidence.residual_induction_measured:
        reasons.append("residual_induction_not_measured")
    elif not evidence.residual_induction_within_bound:
        reasons.append("residual_induction_out_of_bound")
    if not evidence.equivalence_scope:
        reasons.append("equivalence_scope_missing")
    if not evidence.evidence_ref:
        reasons.append("harness_admission_evidence_missing")

    return HarnessAdmissionResult(
        admissible_for_consequence_bearing_work=not reasons,
        reasons=tuple(reasons),
    )


def require_harness_admission(evidence: HarnessAdmissionEvidence) -> None:
    result = verify_harness_admission(evidence)
    if not result.admissible_for_consequence_bearing_work:
        raise HarnessConformanceError(
            "NO_UNGOVERNED_HARNESS_TRANSITION violation: " + ", ".join(result.reasons)
        )


__all__ = [
    "HarnessAdmissionEvidence",
    "HarnessAdmissionResult",
    "HarnessConformanceError",
    "HarnessDescriptor",
    "HarnessState",
    "require_harness_admission",
    "verify_harness_admission",
]
