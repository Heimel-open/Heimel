"""Governed Sentry incident and coding-agent adapter.

The adapter normalizes Sentry production evidence and can build a Seer/coding-
agent handoff request. It does not perform HTTP calls and never grants merge,
deploy, data-mutation, or other execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Sequence


class SentryRepairAction(str, Enum):
    INGEST_INCIDENT = "ingest_incident"
    ROOT_CAUSE = "root_cause"
    HANDOFF_CODING_AGENT = "handoff_coding_agent"
    PROPOSE_PATCH = "propose_patch"
    OPEN_PR = "open_pr"
    MERGE = "merge"
    DEPLOY = "deploy"
    MUTATE_DATA = "mutate_data"


CONSEQUENTIAL_ACTIONS = frozenset(
    {
        SentryRepairAction.MERGE,
        SentryRepairAction.DEPLOY,
        SentryRepairAction.MUTATE_DATA,
    }
)


class OutcomeStatus(str, Enum):
    VERIFIED_NO_RECURRENCE = "verified_no_recurrence"
    STILL_RECURRING = "still_recurring"
    REGRESSION = "regression"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass(frozen=True)
class SentryIncidentEvidence:
    issue_id: str
    project_slug: str
    summary: str
    event_id: str | None = None
    trace_refs: tuple[str, ...] = ()
    release: str | None = None
    repository_ref: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SentryAutofixRequest:
    organization: str
    issue_id: str
    body: Mapping[str, object]
    method: str = "POST"
    authority_effect: str = "none"

    @property
    def path(self) -> str:
        return f"/api/0/organizations/{self.organization}/issues/{self.issue_id}/autofix/"


@dataclass(frozen=True)
class SentryRepairProposal:
    incident: SentryIncidentEvidence
    sentry_run_id: str
    root_cause: str
    patch_ref: str
    validation_refs: tuple[str, ...] = ()
    requested_actions: tuple[SentryRepairAction, ...] = (
        SentryRepairAction.PROPOSE_PATCH,
    )

    def requires_execution_authorization(self) -> bool:
        return any(action in CONSEQUENTIAL_ACTIONS for action in self.requested_actions)


@dataclass(frozen=True)
class PostDeployEvidence:
    issue_id: str
    deployment_ref: str
    verification_window_seconds: int
    before_event_count: int
    after_event_count: int
    trace_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class OutcomeVerification:
    status: OutcomeStatus
    evidence: PostDeployEvidence


class SentryCodingAgentAdapter:
    """Normalize Sentry repair flow without becoming an authority source."""

    allowed_actions = frozenset(
        {
            SentryRepairAction.INGEST_INCIDENT,
            SentryRepairAction.ROOT_CAUSE,
            SentryRepairAction.HANDOFF_CODING_AGENT,
            SentryRepairAction.PROPOSE_PATCH,
            SentryRepairAction.OPEN_PR,
        }
    )
    allowed_stopping_points = frozenset({"root_cause", "solution", "code_changes", "open_pr"})

    def build_coding_agent_handoff(
        self,
        *,
        organization: str,
        incident: SentryIncidentEvidence,
        integration_id: int | None = None,
        provider: str | None = None,
        repo_name: str | None = None,
        user_context: str | None = None,
        stopping_point: str = "code_changes",
    ) -> SentryAutofixRequest:
        """Build, but do not execute, Sentry's coding-agent handoff request."""

        self._validate_incident(incident)
        if not organization.strip():
            raise ValueError("organization is required")
        if integration_id is None and not (provider and provider.strip()):
            raise ValueError("integration_id or provider is required for coding-agent handoff")
        if stopping_point not in self.allowed_stopping_points:
            raise ValueError(f"unsupported stopping_point: {stopping_point}")

        body: dict[str, object] = {
            "step": "coding_agent_handoff",
            "stopping_point": stopping_point,
        }
        if integration_id is not None:
            body["integration_id"] = integration_id
        if provider and provider.strip():
            body["provider"] = provider.strip()
        if repo_name and repo_name.strip():
            body["repo_name"] = repo_name.strip()
        if user_context and user_context.strip():
            body["user_context"] = user_context.strip()

        return SentryAutofixRequest(
            organization=organization.strip(),
            issue_id=incident.issue_id,
            body=body,
        )

    def build_proposal(
        self,
        *,
        incident: SentryIncidentEvidence,
        sentry_run_id: str,
        root_cause: str,
        patch_ref: str,
        validation_refs: Sequence[str] = (),
        requested_actions: Sequence[SentryRepairAction] = (
            SentryRepairAction.PROPOSE_PATCH,
        ),
    ) -> SentryRepairProposal:
        self._validate_incident(incident)
        actions = tuple(requested_actions)
        forbidden = set(actions) - self.allowed_actions
        if forbidden:
            names = ", ".join(sorted(action.value for action in forbidden))
            raise PermissionError(
                f"Sentry adapter has no authority for consequential action(s): {names}"
            )
        if not sentry_run_id.strip():
            raise ValueError("sentry_run_id is required")
        if not root_cause.strip():
            raise ValueError("root_cause is required")
        if not patch_ref.strip():
            raise ValueError("patch_ref is required")

        return SentryRepairProposal(
            incident=incident,
            sentry_run_id=sentry_run_id.strip(),
            root_cause=root_cause.strip(),
            patch_ref=patch_ref.strip(),
            validation_refs=tuple(validation_refs),
            requested_actions=actions,
        )

    def verify_post_deploy(self, evidence: PostDeployEvidence) -> OutcomeVerification:
        if not evidence.issue_id or not evidence.deployment_ref:
            raise ValueError("issue_id and deployment_ref are required")
        if evidence.verification_window_seconds <= 0:
            raise ValueError("verification_window_seconds must be positive")
        if evidence.before_event_count < 0 or evidence.after_event_count < 0:
            raise ValueError("event counts cannot be negative")

        if evidence.before_event_count == 0:
            status = OutcomeStatus.INSUFFICIENT_EVIDENCE
        elif evidence.after_event_count == 0:
            status = OutcomeStatus.VERIFIED_NO_RECURRENCE
        elif evidence.after_event_count > evidence.before_event_count:
            status = OutcomeStatus.REGRESSION
        else:
            status = OutcomeStatus.STILL_RECURRING
        return OutcomeVerification(status=status, evidence=evidence)

    @staticmethod
    def _validate_incident(incident: SentryIncidentEvidence) -> None:
        if not incident.issue_id or not incident.project_slug:
            raise ValueError("incident issue_id and project_slug are required")
        if not incident.summary.strip():
            raise ValueError("incident summary is required")


def next_boundary(proposal: SentryRepairProposal) -> str:
    """Return the next governance boundary without authorizing it."""

    return "REHT_REQUIRED" if proposal.requires_execution_authorization() else "FACTORY_VALIDATE"


__all__ = [
    "CONSEQUENTIAL_ACTIONS",
    "OutcomeStatus",
    "OutcomeVerification",
    "PostDeployEvidence",
    "SentryAutofixRequest",
    "SentryCodingAgentAdapter",
    "SentryIncidentEvidence",
    "SentryRepairAction",
    "SentryRepairProposal",
    "next_boundary",
]
