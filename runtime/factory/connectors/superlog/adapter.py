"""Governed external repair-agent adapter contract.

This adapter normalizes alert-driven investigation output into a Factory-owned
proposal. It deliberately has no merge, deploy, or other execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Sequence


class RepairAction(str, Enum):
    INVESTIGATE = "investigate"
    PROPOSE_PATCH = "propose_patch"
    MERGE = "merge"
    DEPLOY = "deploy"
    MUTATE_DATA = "mutate_data"


CONSEQUENTIAL_ACTIONS = frozenset(
    {RepairAction.MERGE, RepairAction.DEPLOY, RepairAction.MUTATE_DATA}
)


@dataclass(frozen=True)
class IncidentEvidence:
    alert_id: str
    source: str
    summary: str
    trace_refs: tuple[str, ...] = ()
    repository_ref: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RepairProposal:
    incident: IncidentEvidence
    root_cause: str
    patch_ref: str
    validation_refs: tuple[str, ...] = ()
    requested_actions: tuple[RepairAction, ...] = (RepairAction.PROPOSE_PATCH,)

    def requires_execution_authorization(self) -> bool:
        return any(action in CONSEQUENTIAL_ACTIONS for action in self.requested_actions)


class SuperlogRepairAdapter:
    """Normalize external repair-agent results without granting authority."""

    allowed_actions = frozenset({RepairAction.INVESTIGATE, RepairAction.PROPOSE_PATCH})

    def build_proposal(
        self,
        *,
        incident: IncidentEvidence,
        root_cause: str,
        patch_ref: str,
        validation_refs: Sequence[str] = (),
        requested_actions: Sequence[RepairAction] = (RepairAction.PROPOSE_PATCH,),
    ) -> RepairProposal:
        actions = tuple(requested_actions)
        forbidden = set(actions) - self.allowed_actions
        if forbidden:
            names = ", ".join(sorted(action.value for action in forbidden))
            raise PermissionError(
                f"Superlog adapter has no authority for consequential action(s): {names}"
            )
        if not incident.alert_id or not incident.source:
            raise ValueError("incident alert_id and source are required")
        if not root_cause.strip():
            raise ValueError("root_cause is required")
        if not patch_ref.strip():
            raise ValueError("patch_ref is required")
        return RepairProposal(
            incident=incident,
            root_cause=root_cause.strip(),
            patch_ref=patch_ref.strip(),
            validation_refs=tuple(validation_refs),
            requested_actions=actions,
        )


def execution_boundary(proposal: RepairProposal) -> str:
    """Return the next boundary without attempting to authorize execution."""

    return "REHT_REQUIRED" if proposal.requires_execution_authorization() else "FACTORY_VALIDATE"
