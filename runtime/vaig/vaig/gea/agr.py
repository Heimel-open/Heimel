from dataclasses import dataclass

from .types import CandidateAction, GovernanceRoute


@dataclass
class AGRInput:
    action: CandidateAction
    state_admissible: bool
    tad_valid: bool
    integrity_intact: bool
    coherence_class: str
    emergency_active: bool = False


@dataclass
class AGRResult:
    route: GovernanceRoute
    reason: str


class AdaptiveGovernanceRouter:
    """Routes actions through the lightest valid governance path."""

    def route(self, data: AGRInput) -> AGRResult:
        if data.emergency_active:
            return AGRResult(GovernanceRoute.EMERGENCY_MODE, "emergency_mode_active")
        if not data.state_admissible:
            return AGRResult(GovernanceRoute.FULL_GOVERNANCE, "state_not_admissible")
        if not data.tad_valid:
            return AGRResult(GovernanceRoute.FULL_GOVERNANCE, "tad_invalid")
        if not data.integrity_intact:
            return AGRResult(GovernanceRoute.FULL_GOVERNANCE, "continuous_integrity_failed")
        if data.coherence_class.lower() != "high":
            return AGRResult(GovernanceRoute.FULL_GOVERNANCE, "coherence_not_high")
        if data.action.risk_class.value == "A":
            return AGRResult(GovernanceRoute.FAST_PATH, "fast_path_valid")
        if data.action.risk_class.value == "B":
            return AGRResult(GovernanceRoute.STANDARD_VALIDATION, "standard_validation_valid")
        return AGRResult(GovernanceRoute.FULL_GOVERNANCE, "risk_class_c")
