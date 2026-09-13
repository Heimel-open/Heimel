from __future__ import annotations

from ..contracts.common import RISK_ORDER
from ..contracts.function import FunctionDefinition
from .errors import GovernanceError
from .resolver import ResolvedCall

# Evidence minimum-status ordering: parent must be at least as strict.
EVIDENCE_STATUS_ORDER = {
    "RECEIVED": 0,
    "UNVERIFIED": 1,
    "ADMITTED": 2,
    "VERIFIED": 3,
    "CONFIRMED": 4,
}


def check_governance_monotonicity(
    parent: FunctionDefinition, children: list[ResolvedCall]
) -> None:
    """Governance monotonicity (canonical). Composition may only tighten.

      risk(parent) >= max(risk(children))
      effects(parent) ⊇ union(effects(children))       (enforced in effects.py)
      authority(parent) covers capability AND scope of every child requirement
      evidence(parent) covers type AND minimum_status of every child requirement
      rights(parent) covers every child right
      purpose(parent) covers every child purpose
      autonomy(parent) never expands beyond children
    """
    if children:
        max_child_risk = max(RISK_ORDER[c.definition.risk_class] for c in children)
        if RISK_ORDER[parent.risk_class] < max_child_risk:
            raise GovernanceError(
                f"{parent.identity}: risk {parent.risk_class.value} is lower than a child's "
                f"max risk; composition can never lower risk"
            )

    for child in children:
        for req in child.definition.authority_requirements:
            if not _authority_covered(parent.authority_requirements, req):
                raise GovernanceError(
                    f"{parent.identity}: authority requirement {req.capability} scope "
                    f"{sorted(req.scope)} of child {child.definition.identity} is not covered "
                    f"by the parent (capability+scope)"
                )
        for req in child.definition.evidence_requirements:
            if not _evidence_covered(parent.evidence_requirements, req):
                raise GovernanceError(
                    f"{parent.identity}: evidence requirement {req.required_types} at "
                    f"{req.minimum_status} of child {child.definition.identity} is not covered "
                    f"by the parent (type + minimum_status)"
                )
        for req in child.definition.rights_requirements:
            if not _rights_covered(parent.rights_requirements, req):
                raise GovernanceError(
                    f"{parent.identity}: rights requirement {req.required_rights} of child "
                    f"{child.definition.identity} is not covered by the parent"
                )
        for req in child.definition.purpose_requirements:
            if not _purpose_covered(parent.purpose_requirements, req):
                raise GovernanceError(
                    f"{parent.identity}: purpose requirement {req.purpose_types} of child "
                    f"{child.definition.identity} is not covered by the parent"
                )

    parent_autonomy = set(parent.autonomy_profile.allowed_autonomy_levels)
    for child in children:
        child_autonomy = set(child.definition.autonomy_profile.allowed_autonomy_levels)
        if not parent_autonomy.issubset(child_autonomy):
            raise GovernanceError(
                f"{parent.identity}: autonomy {sorted(a.value for a in parent_autonomy)} "
                f"expands beyond child {child.definition.identity} which allows "
                f"{sorted(a.value for a in child_autonomy)}"
            )


def _authority_covered(parent_reqs: list, child_req) -> bool:
    """Parent covers a child authority requirement when a parent requirement
    grants the same capability with scope at least as wide."""
    matching_parent_reqs = [
        r for r in parent_reqs if getattr(r, "capability", None) == getattr(child_req, "capability", None)
    ]
    if not matching_parent_reqs:
        return False
    parent_scope_all: set[str] = set()
    for parent_req in matching_parent_reqs:
        parent_scope_all |= set(getattr(parent_req, "scope", []) or [])
    child_scope = set(getattr(child_req, "scope", []) or [])
    if not child_scope:
        return True
    if "*" in child_scope:
        return "*" in parent_scope_all
    return bool(parent_scope_all) and (child_scope.issubset(parent_scope_all) or "*" in parent_scope_all)


def _evidence_covered(parent_reqs: list, child_req) -> bool:
    """Parent covers a child evidence requirement when every required type is
    required by the parent at a minimum_status at least as strict."""
    for required_type in getattr(child_req, "required_types", []) or []:
        parent_entry = next(
            (r for r in parent_reqs if required_type in (getattr(r, "required_types", []) or [])),
            None,
        )
        if parent_entry is None:
            return False
        parent_level = EVIDENCE_STATUS_ORDER.get(getattr(parent_entry, "minimum_status", "RECEIVED"), 0)
        child_level = EVIDENCE_STATUS_ORDER.get(getattr(child_req, "minimum_status", "RECEIVED"), 0)
        if parent_level < child_level:
            return False
    return True


def _rights_covered(parent_reqs: list, child_req) -> bool:
    parent_rights = {r for req in parent_reqs for r in (getattr(req, "required_rights", []) or [])}
    child_rights = set(getattr(child_req, "required_rights", []) or [])
    return child_rights.issubset(parent_rights)


def _purpose_covered(parent_reqs: list, child_req) -> bool:
    parent_purposes = {p for req in parent_reqs for p in (getattr(req, "purpose_types", []) or [])}
    child_purposes = set(getattr(child_req, "purpose_types", []) or [])
    return child_purposes.issubset(parent_purposes)
