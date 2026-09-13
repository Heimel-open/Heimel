"""Human-established policy recommendations for CMS-neutral content actions.

The evaluator returns an evidence-bound canonical ``ActionDecision`` only. It
cannot issue clearance, create CommitTokens, mutate policy, or execute content.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import rfc8785
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.valo_platform.action_envelope.models import ActionDecision

from .actions import (
    ContentActionCase,
    ContentMateriality,
    ContentOperation,
)


class ContentRiskDomain(str, Enum):
    PRICING = "pricing"
    FINANCIAL = "financial"
    MEDICAL = "medical"
    LEGAL = "legal"
    SAFETY = "safety"
    REGULATED_PRODUCT = "regulated_product"
    PUBLIC_POLICY = "public_policy"
    POLITICS = "politics"
    ELECTIONS = "elections"
    NAMED_PERSON = "named_person"


class ContentRiskEvidence(BaseModel):
    """Typed evidence that may restrict, but never expand, delegated authority."""

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)

    risk_domains: tuple[ContentRiskDomain, ...] = ()
    unsupported_claims: bool = False
    missing_provenance: bool = False
    schema_mismatch: bool = False
    stale_content_state: bool = False
    semantic_uncertainty: bool = False
    rights_ambiguity: bool = False
    cross_market: bool = False
    cross_language: bool = False
    halt_required: bool = False
    audience_count: int = Field(default=1, ge=0)

    @field_validator("risk_domains", mode="before")
    @classmethod
    def normalize_domains(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        values = [value] if isinstance(value, str) else list(value)
        normalized = {
            item.value if isinstance(item, ContentRiskDomain) else str(item)
            for item in values
        }
        return tuple(sorted(normalized))


class ContentPolicyProfile(BaseModel):
    """Frozen human-established scope and bounded automation thresholds."""

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
    authority_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    mandate_ref: str = Field(min_length=1)
    mandate_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    allowed_principal_ids: tuple[str, ...] = Field(min_length=1)
    allowed_content_systems: tuple[str, ...] = Field(min_length=1)
    allowed_workspace_refs: tuple[str, ...] = Field(min_length=1)
    allowed_project_refs: tuple[str, ...] = Field(min_length=1)
    allowed_dataset_refs: tuple[str, ...] = Field(min_length=1)
    allowed_operations: tuple[ContentOperation, ...] = Field(min_length=1)
    allowed_markets: tuple[str, ...] = Field(min_length=1)
    allowed_languages: tuple[str, ...] = Field(min_length=1)
    allowed_jurisdictions: tuple[str, ...] = Field(min_length=1)
    allowed_channels: tuple[str, ...] = Field(min_length=1)

    auto_clear_operations: tuple[ContentOperation, ...] = ()
    step_up_operations: tuple[ContentOperation, ...] = (
        ContentOperation.PUBLISH,
        ContentOperation.DELETE,
        ContentOperation.UPDATE_SCHEMA,
        ContentOperation.MIGRATE,
        ContentOperation.BULK_UPDATE,
    )
    max_auto_materiality: ContentMateriality = ContentMateriality.LOW
    max_uncertainty: float = Field(default=0.10, ge=0.0, le=1.0)
    max_batch_size: int = Field(default=1, ge=1)
    max_audience_count: int = Field(default=1, ge=0)
    max_unique_markets: int = Field(default=1, ge=1)
    max_unique_locales: int = Field(default=1, ge=1)
    max_cumulative_materiality_score: int = Field(default=2, ge=0)
    required_approver_roles: tuple[str, ...] = Field(
        default=("content_owner",), min_length=1
    )

    effective_from: datetime
    effective_until: datetime | None = None

    @field_validator(
        "allowed_principal_ids",
        "allowed_content_systems",
        "allowed_workspace_refs",
        "allowed_project_refs",
        "allowed_dataset_refs",
        "allowed_markets",
        "allowed_languages",
        "allowed_jurisdictions",
        "allowed_channels",
        "required_approver_roles",
        mode="before",
    )
    @classmethod
    def normalize_strings(cls, value: Any) -> tuple[str, ...]:
        values = [value] if isinstance(value, str) else list(value)
        normalized: set[str] = set()
        for item in values:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("policy collections require non-empty strings")
            normalized.add(item.strip())
        return tuple(sorted(normalized))

    @field_validator(
        "allowed_operations", "auto_clear_operations", "step_up_operations",
        mode="before",
    )
    @classmethod
    def normalize_operations(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        values = [value] if isinstance(value, str) else list(value)
        normalized = {
            item.value if isinstance(item, ContentOperation) else str(item)
            for item in values
        }
        return tuple(sorted(normalized))

    @field_validator("effective_from", "effective_until")
    @classmethod
    def require_aware_time(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("policy effective times must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_profile(self) -> "ContentPolicyProfile":
        if self.effective_until is not None and self.effective_until <= self.effective_from:
            raise ValueError("effective_until must be after effective_from")
        allowed = set(self.allowed_operations)
        if not set(self.auto_clear_operations).issubset(allowed):
            raise ValueError("auto-clear operations must be inside allowed operations")
        if not set(self.step_up_operations).issubset(allowed):
            raise ValueError("step-up operations must be inside allowed operations")
        if set(self.auto_clear_operations) & set(self.step_up_operations):
            raise ValueError("an operation cannot be both auto-clear and step-up")
        return self

    def canonical_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def digest(self) -> str:
        encoded = rfc8785.dumps(self.canonical_payload())
        return "sha256:" + hashlib.sha256(encoded).hexdigest()

    def is_active(self, now: datetime) -> bool:
        current = _as_utc(now)
        if current < _as_utc(self.effective_from):
            return False
        if self.effective_until is not None and current >= _as_utc(
            self.effective_until
        ):
            return False
        return True


class ContentPolicyEvaluation(BaseModel):
    """Evidence-bound recommendation; explicitly not a clearance artifact."""

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)

    decision: ActionDecision
    case_hash: str
    payload_digest: str
    target_digest: str
    state_binding_digest: str
    policy_digest: str
    risk_domains: tuple[ContentRiskDomain, ...] = ()
    reasons: tuple[str, ...]
    required_approver_roles: tuple[str, ...] = ()
    evaluated_at: datetime


_MATERIALITY_SCORE = {
    ContentMateriality.LOW: 1,
    ContentMateriality.MEDIUM: 2,
    ContentMateriality.HIGH: 3,
    ContentMateriality.CRITICAL: 4,
}


class ContentPolicyEvaluator:
    """Evaluate an exact Content Action Case under one frozen policy profile."""

    def evaluate(
        self,
        *,
        action_case: ContentActionCase,
        policy: ContentPolicyProfile,
        risk: ContentRiskEvidence,
        now: datetime | None = None,
    ) -> ContentPolicyEvaluation:
        evaluated_at = _as_utc(now or datetime.now(timezone.utc))
        policy_digest = policy.digest()

        scope_reasons = self._scope_reasons(action_case, policy)
        if scope_reasons:
            return self._result(
                ActionDecision.DENY,
                action_case,
                policy_digest,
                risk,
                scope_reasons,
                evaluated_at,
            )

        if risk.halt_required:
            return self._result(
                ActionDecision.HALT,
                action_case,
                policy_digest,
                risk,
                ["content risk evidence requires an immediate halt"],
                evaluated_at,
                policy.required_approver_roles,
            )

        deferred = self._defer_reasons(action_case, policy, risk, evaluated_at)
        if deferred:
            return self._result(
                ActionDecision.DEFER,
                action_case,
                policy_digest,
                risk,
                deferred,
                evaluated_at,
            )

        escalation = self._step_up_reasons(action_case, policy, risk)
        if escalation:
            return self._result(
                ActionDecision.STEP_UP,
                action_case,
                policy_digest,
                risk,
                escalation,
                evaluated_at,
                policy.required_approver_roles,
            )

        operation = action_case.content.operation
        if action_case.is_observation:
            return self._result(
                ActionDecision.ALLOW,
                action_case,
                policy_digest,
                risk,
                ["observation is inside the established content policy scope"],
                evaluated_at,
            )

        if operation not in policy.auto_clear_operations:
            return self._result(
                ActionDecision.STEP_UP,
                action_case,
                policy_digest,
                risk,
                ["policy does not permit bounded automatic recommendation"],
                evaluated_at,
                policy.required_approver_roles,
            )

        return self._result(
            ActionDecision.ALLOW,
            action_case,
            policy_digest,
            risk,
            ["proposal is inside the explicit low-risk content mandate"],
            evaluated_at,
        )

    @staticmethod
    def _scope_reasons(
        action_case: ContentActionCase,
        policy: ContentPolicyProfile,
    ) -> list[str]:
        content = action_case.content
        record = action_case.action_case
        checks = (
            (content.tenant_id == policy.tenant_id, "tenant is outside policy scope"),
            (
                content.principal_id in policy.allowed_principal_ids,
                "principal is outside policy scope",
            ),
            (
                content.delegated_mandate_ref == policy.mandate_ref,
                "mandate reference does not match policy",
            ),
            (
                record.mandate_fingerprint == policy.mandate_fingerprint,
                "mandate fingerprint does not match policy",
            ),
            (
                content.content_system in policy.allowed_content_systems,
                "content system is outside policy scope",
            ),
            (
                content.workspace_ref in policy.allowed_workspace_refs,
                "workspace is outside policy scope",
            ),
            (
                content.project_ref in policy.allowed_project_refs,
                "project is outside policy scope",
            ),
            (
                content.dataset_ref in policy.allowed_dataset_refs,
                "dataset is outside policy scope",
            ),
            (
                content.operation in policy.allowed_operations,
                "operation is outside policy scope",
            ),
            (content.market in policy.allowed_markets, "market is outside policy scope"),
            (
                content.language in policy.allowed_languages,
                "language is outside policy scope",
            ),
            (
                set(content.jurisdictions).issubset(policy.allowed_jurisdictions),
                "jurisdiction is outside policy scope",
            ),
            (
                set(content.channels).issubset(policy.allowed_channels),
                "channel is outside policy scope",
            ),
        )
        return [reason for allowed, reason in checks if not allowed]

    @staticmethod
    def _defer_reasons(
        action_case: ContentActionCase,
        policy: ContentPolicyProfile,
        risk: ContentRiskEvidence,
        now: datetime,
    ) -> list[str]:
        content = action_case.content
        reasons: list[str] = []
        if not policy.is_active(now):
            reasons.append("content policy is outside its effective window")
        if content.policy_snapshot_digest != policy.digest():
            reasons.append("content policy snapshot is stale or mismatched")
        if risk.missing_provenance or not content.provenance_refs:
            reasons.append("content provenance is missing or incomplete")
        if risk.unsupported_claims:
            reasons.append("content claims require additional evidence")
        if risk.schema_mismatch:
            reasons.append("content schema binding is stale or mismatched")
        if risk.stale_content_state:
            reasons.append("content state binding is stale or mismatched")
        if (
            risk.cross_market or risk.cross_language
        ) and not content.semantic_evidence_refs:
            reasons.append("cross-market or cross-language action lacks semantic evidence")
        return reasons

    @staticmethod
    def _step_up_reasons(
        action_case: ContentActionCase,
        policy: ContentPolicyProfile,
        risk: ContentRiskEvidence,
    ) -> list[str]:
        content = action_case.content
        reasons: list[str] = []
        if content.operation in policy.step_up_operations:
            reasons.append(
                f"operation requires explicit human approval: {content.operation.value}"
            )
        if risk.risk_domains:
            reasons.append(
                "high-risk content domain requires human approval: "
                + ", ".join(domain.value for domain in risk.risk_domains)
            )
        if risk.rights_ambiguity:
            reasons.append("rights or licensing evidence is ambiguous")
        if risk.semantic_uncertainty and (
            risk.cross_market or risk.cross_language
        ):
            reasons.append("cross-market or cross-language semantics are uncertain")
        if content.uncertainty > policy.max_uncertainty:
            reasons.append("content uncertainty exceeds delegated threshold")
        if (
            _MATERIALITY_SCORE[content.materiality]
            > _MATERIALITY_SCORE[policy.max_auto_materiality]
        ):
            reasons.append("content materiality exceeds delegated threshold")
        if content.batch_size > policy.max_batch_size:
            reasons.append("content batch exceeds delegated threshold")
        if risk.audience_count > policy.max_audience_count:
            reasons.append("affected audience exceeds delegated threshold")
        return reasons

    @staticmethod
    def _result(
        decision: ActionDecision,
        action_case: ContentActionCase,
        policy_digest: str,
        risk: ContentRiskEvidence,
        reasons: list[str],
        evaluated_at: datetime,
        required_approver_roles: tuple[str, ...] = (),
    ) -> ContentPolicyEvaluation:
        return ContentPolicyEvaluation(
            decision=decision,
            case_hash=action_case.action_case.case_hash,
            payload_digest=action_case.digest(),
            target_digest=action_case.target_digest(),
            state_binding_digest=action_case.state_binding_digest(),
            policy_digest=policy_digest,
            risk_domains=risk.risk_domains,
            reasons=tuple(reasons),
            required_approver_roles=required_approver_roles,
            evaluated_at=evaluated_at,
        )


def materiality_score(value: ContentMateriality) -> int:
    return _MATERIALITY_SCORE[value]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("time must be timezone-aware")
    return value.astimezone(timezone.utc)
