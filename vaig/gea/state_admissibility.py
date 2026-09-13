from dataclasses import dataclass
from typing import List

from .types import GovernanceContext


@dataclass
class StateAdmissibilityResult:
    admissible: bool
    reason: str
    state_hash: str
    evidence_refs: List[str]


class StateAdmissibilityGate:
    """Pre-governance check: is represented reality admissible?"""

    def evaluate(self, context: GovernanceContext) -> StateAdmissibilityResult:
        if not context.state_hash:
            return StateAdmissibilityResult(False, "missing_state_hash", "", [])
        if not context.evidence_hash:
            return StateAdmissibilityResult(False, "missing_evidence_hash", context.state_hash, [])
        if context.metadata.get("stale") is True:
            return StateAdmissibilityResult(False, "state_stale", context.state_hash, [context.evidence_hash])
        if context.metadata.get("contested") is True:
            return StateAdmissibilityResult(False, "state_contested", context.state_hash, [context.evidence_hash])
        return StateAdmissibilityResult(True, "state_admissible", context.state_hash, [context.evidence_hash])
