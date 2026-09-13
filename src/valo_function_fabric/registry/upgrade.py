from __future__ import annotations

from ..contracts.common import RISK_ORDER, GovernanceChange
from ..contracts.function import FunctionDefinition


class UpgradeComparison:
    """Compare two versions of a Function and detect governance changes.
    Governance-affecting changes are BREAKING_GOVERNANCE_CHANGE, not just a
    semantic version bump."""

    def __init__(self, old: FunctionDefinition, new: FunctionDefinition) -> None:
        self.old = old
        self.new = new

    def changes(self) -> list[GovernanceChange]:
        changes: list[GovernanceChange] = []
        if self.old.input_type != self.new.input_type:
            changes.append(GovernanceChange.INPUT_CHANGED)
        if self.old.output_type != self.new.output_type:
            changes.append(GovernanceChange.OUTPUT_CHANGED)
        if set(self.old.effects) != set(self.new.effects):
            new_only = set(self.new.effects) - set(self.old.effects)
            if new_only:
                changes.append(GovernanceChange.EFFECTS_INCREASED)
        if self.old.risk_class != self.new.risk_class and RISK_ORDER[self.new.risk_class] > RISK_ORDER[self.old.risk_class]:
            changes.append(GovernanceChange.RISK_CHANGED)
        if _requirements_weakened(self.old.authority_requirements, self.new.authority_requirements):
            changes.append(GovernanceChange.AUTHORITY_WEAKENED)
        if _requirements_weakened(self.old.evidence_requirements, self.new.evidence_requirements):
            changes.append(GovernanceChange.EVIDENCE_WEAKENED)
        if _autonomy_expanded(self.old.autonomy_profile.allowed_autonomy_levels, self.new.autonomy_profile.allowed_autonomy_levels):
            changes.append(GovernanceChange.AUTONOMY_EXPANDED)
        return changes

    def is_breaking_governance(self) -> bool:
        breaking = {
            GovernanceChange.EFFECTS_INCREASED,
            GovernanceChange.RISK_CHANGED,
            GovernanceChange.AUTHORITY_WEAKENED,
            GovernanceChange.EVIDENCE_WEAKENED,
            GovernanceChange.AUTONOMY_EXPANDED,
        }
        return any(c in breaking for c in self.changes())

    def breaking_change_label(self) -> GovernanceChange:
        """The single most severe governance change, if any."""
        if not self.is_breaking_governance():
            return GovernanceChange.NONE
        for change in (
            GovernanceChange.AUTONOMY_EXPANDED,
            GovernanceChange.EFFECTS_INCREASED,
            GovernanceChange.RISK_CHANGED,
            GovernanceChange.AUTHORITY_WEAKENED,
            GovernanceChange.EVIDENCE_WEAKENED,
        ):
            if change in self.changes():
                return change
        return GovernanceChange.BREAKING_GOVERNANCE_CHANGE


def _requirements_weakened(old: list, new: list) -> bool:
    """A requirement set is weakened if the new version drops a capability that
    the old version required (per-requirement, same capability)."""
    old_map: dict = {}
    for r in old:
        key = _requirement_key(r)
        old_map[key] = r
    new_map: dict = {}
    for r in new:
        key = _requirement_key(r)
        new_map[key] = r
    for key, old_req in old_map.items():
        new_req = new_map.get(key)
        if new_req is None:
            return True  # requirement removed entirely
        old_scope = set(getattr(old_req, "scope", []) or [])
        new_scope = set(getattr(new_req, "scope", []) or [])
        if new_scope and old_scope and not new_scope.issuperset(old_scope):
            return True
    return False


def _requirement_key(requirement) -> tuple:
    capability = getattr(requirement, "capability", None)
    if capability is not None:
        return ("capability", capability)
    required_types = getattr(requirement, "required_types", None)
    if required_types is not None:
        return ("types", tuple(required_types))
    return ("empty", "")


def _autonomy_expanded(old: list, new: list) -> bool:
    old_set = set(old)
    new_set = set(new)
    return bool(new_set - old_set)
