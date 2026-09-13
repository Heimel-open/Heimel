"""Human-in-the-Lead policy profile for governed publication.

The human or institution defines the mandate, scope and escalation thresholds.
This module evaluates an exact publication proposal against that frozen profile.
It returns a canonical decision recommendation but never issues clearance,
creates a CommitToken, or executes a publication.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import rfc8785
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.valo_platform.action_envelope.models import ActionDecision

from .publication import PublicationActionCase, PublicationPrivacy


class PublicationRiskDomain(str, Enum):
    POLITICS = "politics"
    ELECTIONS = "elections"
    PUBLIC_POLICY = "public_policy"
    NAMED_PERSON = "named_person"
    MEDICAL = "medical"
    LEGAL = "legal"
    FINANCIAL = "financial"
    SAFETY = "safety"
    REGULATED_PRODUCT = "regulated_product"


class PublicationRiskEvidence(BaseModel):
    """Typed risk evidence supplied to policy evaluation.

    The evidence can trigger escalation or deferral. It cannot grant authority
    or lower thresholds in the policy profile.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    risk_domains: tuple[PublicationRiskDomain, ...] = ()
    unsupported_claims: bool = False
    rights_ambiguity: bool = False
    semantic_uncertainty: bool = False
    proposed_publications_24h: int = Field(default=1, ge=0)
    batch_size: int = Field(default=1, ge=1)
    estimated_spend: float = Field(default=0.0, ge=0.0)

    @field_validator("risk_domains", mode="before")
    @classmethod
    def normalize_domains(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        values = [value] if isinstance(value, str) else list(value)
        return tuple(sorted({str(item.value if isinstance(item, Enum) else item) for item in values}))


class PublicationPolicyProfile(BaseModel):
    """Frozen human-established mandate and automatic-clearance boundary."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        use_enum_values=False,
    )

    policy_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    established_by: str = Field(min_length=1)
    authority_ref: str = Field(min_length=1)
    mandate_ref: str = Field(min_length=1)
    mandate_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    allowed_principal_ids: tuple[str, ...] = Field(min_length=1)
    allowed_providers: tuple[str, ...] = Field(min_length=1)
    allowed_account_refs: tuple[str, ...] = Field(min_length=1)
    allowed_channel_refs: tuple[str, ...] = Field(min_length=1)
    allowed_languages: tuple[str, ...] = Field(min_length=1)
    allowed_jurisdictions: tuple[str, ...] = Field(min_length=1)

    auto_clear_low_risk: bool = False
    allow_public_autoclear: bool = False
    max_publications_24h: int = Field(default=1, ge=1)
    max_batch_size: int = Field(default=1, ge=1)
    max_spend: float = Field(default=0.0, ge=0.0)
    max_schedule_horizon_hours: int = Field(default=168, ge=0)
    required_approver_roles: tuple[str, ...] = Field(default=("publisher",), min_length=1)

    effective_from: datetime
    effective_until: datetime | None = None

    @field_validator(
        "allowed_principal_ids",
        "allowed_providers",
        "allowed_account_refs",
        "allowed_channel_refs",
        "allowed_languages",
        "allowed_jurisdictions",
        "required_approver_roles",
        mode="before",
    )
    @classmethod
    def normalize_string_sets(cls, value: Any) -> tuple[str, ...]:
        if isinstance(value, str):
            raw = [value]
        else:
            raw = list(value)
        normalized: set[str] = set()
        for item in raw:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("policy collections may contain only non-empty strings")
            normalized.add(item.strip())
        return tuple(sorted(normalized))

    @field_validator("effective_from", "effective_until")
    @classmethod
    def require_aware_time(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("policy effective times must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_window(self) -> "PublicationPolicyProfile":
        if self.effective_until is not None and self.effective_until <= self.effective_from:
            raise ValueError("effective_until must be after effective_from")
        return self

    def canonical_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def digest(self) -> str:
        return "sha256:" + hashlib.sha256(rfc8785.dumps(self.canonical_payload())).hexdigest()

    def is_active(self, now: datetime) -> bool:
        now = _as_utc(now)
        if now < _as_utc(self.effective_from):
            return False
        if self.effective_until is not None and now >= _as_utc(self.effective_until):
            return False
        return True


class PublicationPolicyEvaluation(BaseModel):
    """Evidence-bound policy outcome; not an execution clearance."""

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)

    decision: ActionDecision
    case_hash: str
    payload_digest: str
    policy_digest: str
    reasons: tuple[str, ...]
    required_approver_roles: tuple[str, ...] = ()
    evaluated_at: datetime


class PublicationPolicyEvaluator:
    """Evaluate a proposal under a human-established publication profile."""

    def evaluate(
        self,
        *,
        action_case: PublicationActionCase,
        policy: PublicationPolicyProfile,
        risk: PublicationRiskEvidence,
        now: datetime | None = None,
    ) -> PublicationPolicyEvaluation:
        now = _as_utc(now or datetime.now(timezone.utc))
        policy_digest = policy.digest()

        scope_reasons = self._scope_reasons(action_case, policy)
        if scope_reasons:
            return self._result(
                ActionDecision.DENY,
                action_case,
                policy_digest,
                scope_reasons,
                now,
            )

        deferred: list[str] = []
        if not policy.is_active(now):
            deferred.append("publication policy is outside its effective window")
        if action_case.publication.policy_snapshot_digest != policy_digest:
            deferred.append("publication policy snapshot is stale or mismatched")
        scheduled_for = action_case.publication.scheduled_for
        if scheduled_for is not None and _as_utc(scheduled_for) < now:
            deferred.append("scheduled publication time is in the past")
        if risk.unsupported_claims:
            deferred.append("factual claims require additional supporting evidence")
        if deferred:
            return self._result(
                ActionDecision.DEFER,
                action_case,
                policy_digest,
                deferred,
                now,
            )

        escalation = self._step_up_reasons(action_case, policy, risk, now)
        if escalation:
            return self._result(
                ActionDecision.STEP_UP,
                action_case,
                policy_digest,
                escalation,
                now,
                policy.required_approver_roles,
            )

        if not policy.auto_clear_low_risk:
            return self._result(
                ActionDecision.STEP_UP,
                action_case,
                policy_digest,
                ["policy does not permit bounded automatic clearance"],
                now,
                policy.required_approver_roles,
            )

        return self._result(
            ActionDecision.ALLOW,
            action_case,
            policy_digest,
            ["proposal is inside the explicit low-risk publication mandate"],
            now,
        )

    @staticmethod
    def _scope_reasons(
        action_case: PublicationActionCase,
        policy: PublicationPolicyProfile,
    ) -> list[str]:
        publication = action_case.publication
        record = action_case.action_case
        reasons: list[str] = []
        checks = (
            (publication.tenant_id == policy.tenant_id, "tenant is outside publication policy scope"),
            (publication.principal_id in policy.allowed_principal_ids, "principal is outside publication policy scope"),
            (publication.delegated_mandate_ref == policy.mandate_ref, "mandate reference does not match publication policy"),
            (record.mandate_fingerprint == policy.mandate_fingerprint, "mandate fingerprint does not match publication policy"),
            (publication.provider in policy.allowed_providers, "provider is outside publication policy scope"),
            (publication.account_ref in policy.allowed_account_refs, "account is outside publication policy scope"),
            (publication.channel_ref in policy.allowed_channel_refs, "channel is outside publication policy scope"),
            (publication.language in policy.allowed_languages, "language is outside publication policy scope"),
            (set(publication.jurisdictions).issubset(policy.allowed_jurisdictions), "jurisdiction is outside publication policy scope"),
        )
        for allowed, reason in checks:
            if not allowed:
                reasons.append(reason)
        return reasons

    @staticmethod
    def _step_up_reasons(
        action_case: PublicationActionCase,
        policy: PublicationPolicyProfile,
        risk: PublicationRiskEvidence,
        now: datetime,
    ) -> list[str]:
        reasons: list[str] = []
        if risk.risk_domains:
            reasons.append(
                "high-risk content domain requires human approval: "
                + ", ".join(domain.value for domain in risk.risk_domains)
            )
        if risk.rights_ambiguity:
            reasons.append("rights or licensing evidence is ambiguous")
        if risk.semantic_uncertainty:
            reasons.append("cross-language semantic stability is uncertain")
        if risk.proposed_publications_24h > policy.max_publications_24h:
            reasons.append("publishing frequency exceeds delegated threshold")
        if risk.batch_size > policy.max_batch_size:
            reasons.append("publication batch exceeds delegated threshold")
        if risk.estimated_spend > policy.max_spend:
            reasons.append("publication spend exceeds delegated threshold")
        if (
            action_case.publication.privacy_status is PublicationPrivacy.PUBLIC
            and not policy.allow_public_autoclear
        ):
            reasons.append("public visibility requires human approval")
        scheduled_for = action_case.publication.scheduled_for
        if scheduled_for is not None:
            horizon_hours = (_as_utc(scheduled_for) - now).total_seconds() / 3600
            if horizon_hours > policy.max_schedule_horizon_hours:
                reasons.append("publication schedule exceeds delegated horizon")
        return reasons

    @staticmethod
    def _result(
        decision: ActionDecision,
        action_case: PublicationActionCase,
        policy_digest: str,
        reasons: list[str],
        now: datetime,
        required_approver_roles: tuple[str, ...] = (),
    ) -> PublicationPolicyEvaluation:
        return PublicationPolicyEvaluation(
            decision=decision,
            case_hash=action_case.action_case.case_hash,
            payload_digest=action_case.digest(),
            policy_digest=policy_digest,
            reasons=tuple(reasons),
            required_approver_roles=required_approver_roles,
            evaluated_at=now,
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("time must be timezone-aware")
    return value.astimezone(timezone.utc)
