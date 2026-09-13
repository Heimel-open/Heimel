"""CMS-neutral action contracts for Governed Content Operations.

The contracts in this module describe and hash an exact content observation or
proposed mutation. They compose over the canonical ``ActionCaseRecord`` and do
not evaluate policy, issue clearance, or execute an external write.
"""

from __future__ import annotations

import hashlib
import re
from enum import Enum
from typing import Any

import rfc8785
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.valo_platform.action_envelope.models import ActionType, Reversibility
from src.valo_platform.decision_governance.action_case import ActionCaseRecord


_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _validate_sha256(value: str) -> str:
    if not _SHA256_RE.fullmatch(value):
        raise ValueError("digest must be lowercase sha256:<64 hex>")
    return value


def _digest(payload: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(rfc8785.dumps(payload)).hexdigest()


class ContentEffect(str, Enum):
    """Whether an operation only observes state or proposes a state change."""

    OBSERVATION = "observation"
    MUTATION = "mutation"


class ContentOperation(str, Enum):
    """Provider-neutral content operation taxonomy."""

    QUERY = "content.query"
    CREATE_DRAFT = "content.create_draft"
    UPDATE_FIELD = "content.update_field"
    BULK_UPDATE = "content.bulk_update"
    PUBLISH = "content.publish"
    UNPUBLISH = "content.unpublish"
    ARCHIVE = "content.archive"
    DELETE = "content.delete"
    MIGRATE = "content.migrate"
    LOCALIZE = "content.localize"
    ATTACH_ASSET = "content.attach_asset"
    UPDATE_TAXONOMY = "content.update_taxonomy"
    UPDATE_SCHEMA = "content.update_schema"

    @property
    def effect(self) -> ContentEffect:
        return _EFFECT_BY_OPERATION[self]

    @property
    def action_type(self) -> ActionType:
        """Map the content verb to an existing canonical transition category."""

        return _ACTION_TYPE_BY_OPERATION[self]

    @property
    def requires_mutation_clearance(self) -> bool:
        return self.effect is ContentEffect.MUTATION


_EFFECT_BY_OPERATION = {
    operation: (
        ContentEffect.OBSERVATION
        if operation is ContentOperation.QUERY
        else ContentEffect.MUTATION
    )
    for operation in ContentOperation
}

_ACTION_TYPE_BY_OPERATION = {
    ContentOperation.QUERY: ActionType.GENERATE_REPORT,
    ContentOperation.CREATE_DRAFT: ActionType.STATE_TRANSITION,
    ContentOperation.UPDATE_FIELD: ActionType.STATE_TRANSITION,
    ContentOperation.BULK_UPDATE: ActionType.STATE_TRANSITION,
    ContentOperation.PUBLISH: ActionType.EXTERNAL_PUBLICATION,
    ContentOperation.UNPUBLISH: ActionType.STATE_TRANSITION,
    ContentOperation.ARCHIVE: ActionType.STATE_TRANSITION,
    ContentOperation.DELETE: ActionType.DELETE_RESOURCE,
    ContentOperation.MIGRATE: ActionType.STATE_TRANSITION,
    ContentOperation.LOCALIZE: ActionType.STATE_TRANSITION,
    ContentOperation.ATTACH_ASSET: ActionType.STATE_TRANSITION,
    ContentOperation.UPDATE_TAXONOMY: ActionType.STATE_TRANSITION,
    ContentOperation.UPDATE_SCHEMA: ActionType.CONFIGURATION_CHANGE,
}


class ContentMateriality(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ContentApprovalRequirement(str, Enum):
    NONE = "none"
    POLICY = "policy"
    EXPLICIT = "explicit"


class ContentChangeReference(BaseModel):
    """Reference to a proposed patch or transformation, never raw content."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    change_ref: str = Field(min_length=1)
    digest: str
    media_type: str | None = None

    @field_validator("digest")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        return _validate_sha256(value)


class ContentAction(BaseModel):
    """Exact CMS-neutral observation or proposed mutation payload."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        use_enum_values=False,
    )

    tenant_id: str = Field(min_length=1)
    principal_id: str = Field(min_length=1)
    delegated_mandate_ref: str = Field(min_length=1)
    purpose_ref: str = Field(min_length=1)

    operation: ContentOperation
    content_system: str = Field(min_length=1)
    workspace_ref: str = Field(min_length=1)
    project_ref: str = Field(min_length=1)
    dataset_ref: str = Field(min_length=1)

    record_ids: tuple[str, ...] = Field(min_length=1)
    content_type: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    affected_fields: tuple[str, ...] = ()
    locales: tuple[str, ...] = Field(min_length=1)
    source_version_refs: tuple[str, ...] = Field(min_length=1)
    target_version_refs: tuple[str, ...] = ()
    proposed_change: ContentChangeReference | None = None

    batch_id: str | None = None
    batch_size: int = Field(default=1, ge=1)

    market: str = Field(min_length=1)
    language: str = Field(min_length=1)
    jurisdictions: tuple[str, ...] = Field(min_length=1)
    channels: tuple[str, ...] = Field(min_length=1)

    provenance_refs: tuple[str, ...] = Field(min_length=1)
    policy_refs: tuple[str, ...] = Field(min_length=1)
    semantic_evidence_refs: tuple[str, ...] = ()
    rights_evidence_refs: tuple[str, ...] = ()

    materiality: ContentMateriality
    affected_audiences: tuple[str, ...] = Field(min_length=1)
    reversibility: Reversibility
    rollback_ref: str | None = None
    approval_requirement: ContentApprovalRequirement
    approver_roles: tuple[str, ...] = ()

    confidence: float = Field(ge=0.0, le=1.0)
    uncertainty: float = Field(ge=0.0, le=1.0)
    expected_effect: str = Field(min_length=1)

    idempotency_key: str | None = None
    content_snapshot_digest: str
    policy_snapshot_digest: str

    @field_validator(
        "record_ids",
        "affected_fields",
        "locales",
        "source_version_refs",
        "target_version_refs",
        "jurisdictions",
        "channels",
        "provenance_refs",
        "policy_refs",
        "semantic_evidence_refs",
        "rights_evidence_refs",
        "affected_audiences",
        "approver_roles",
        mode="before",
    )
    @classmethod
    def normalize_string_collections(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        values = [value] if isinstance(value, str) else list(value)
        normalized: set[str] = set()
        for item in values:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("string collections may contain only non-empty strings")
            normalized.add(item.strip())
        return tuple(sorted(normalized))

    @field_validator("content_snapshot_digest", "policy_snapshot_digest")
    @classmethod
    def validate_digests(cls, value: str) -> str:
        return _validate_sha256(value)

    @model_validator(mode="after")
    def validate_operation_shape(self) -> "ContentAction":
        if self.batch_size < len(self.record_ids):
            raise ValueError("batch_size cannot be smaller than the bound record set")
        if self.batch_size > 1 and not self.batch_id:
            raise ValueError("batch_id is required when batch_size exceeds one")

        if self.operation.effect is ContentEffect.OBSERVATION:
            if self.proposed_change is not None:
                raise ValueError("observation actions cannot carry a proposed mutation")
            if self.idempotency_key is not None:
                raise ValueError("observation actions cannot carry a mutation idempotency key")
            if self.target_version_refs:
                raise ValueError("observation actions cannot declare target versions")
        else:
            if self.proposed_change is None:
                raise ValueError("mutation actions require a proposed change reference")
            if not self.idempotency_key:
                raise ValueError("mutation actions require an idempotency key")
            if not self.affected_fields and self.operation not in {
                ContentOperation.PUBLISH,
                ContentOperation.UNPUBLISH,
                ContentOperation.ARCHIVE,
                ContentOperation.DELETE,
            }:
                raise ValueError("field-affecting mutations require affected_fields")

        if self.reversibility in {
            Reversibility.REVERSIBLE,
            Reversibility.PARTIALLY_REVERSIBLE,
        } and not self.rollback_ref:
            raise ValueError("reversible mutations require a rollback reference")

        if (
            self.approval_requirement is ContentApprovalRequirement.EXPLICIT
            and not self.approver_roles
        ):
            raise ValueError("explicit approval requires at least one approver role")
        return self

    def canonical_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def digest(self) -> str:
        return _digest(self.canonical_payload())

    def target_digest(self) -> str:
        """Bind the exact CMS destination, record set, locale and channel scope."""

        return _digest(
            {
                "tenant_id": self.tenant_id,
                "content_system": self.content_system,
                "workspace_ref": self.workspace_ref,
                "project_ref": self.project_ref,
                "dataset_ref": self.dataset_ref,
                "record_ids": self.record_ids,
                "locales": self.locales,
                "channels": self.channels,
            }
        )

    def state_binding_digest(self) -> str:
        return _digest(
            {
                "schema_version": self.schema_version,
                "source_version_refs": self.source_version_refs,
                "content_snapshot_digest": self.content_snapshot_digest,
                "policy_snapshot_digest": self.policy_snapshot_digest,
            }
        )


class ContentActionCase(BaseModel):
    """Content-specific composition over one canonical Action Case version."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action_case: ActionCaseRecord
    content: ContentAction

    @model_validator(mode="after")
    def validate_canonical_bindings(self) -> "ContentActionCase":
        record = self.action_case
        content = self.content

        if record.tenant_id != content.tenant_id:
            raise ValueError("content tenant does not match canonical Action Case")
        if record.action_class != content.operation.action_type:
            raise ValueError("content operation does not match canonical ActionType")
        if record.mandate_ref != content.delegated_mandate_ref:
            raise ValueError("content mandate does not match canonical Action Case")
        _validate_sha256(record.case_hash)

        evidence = set(content.provenance_refs)
        evidence.update(content.semantic_evidence_refs)
        evidence.update(content.rights_evidence_refs)
        missing_evidence = set(record.evidence_refs) - evidence
        if missing_evidence:
            raise ValueError(
                "content payload does not bind canonical Action Case evidence: "
                + ", ".join(sorted(missing_evidence))
            )

        missing_policy = set(record.policy_refs) - set(content.policy_refs)
        if missing_policy:
            raise ValueError(
                "content payload does not bind canonical Action Case policy: "
                + ", ".join(sorted(missing_policy))
            )
        if (
            record.policy_fingerprint is not None
            and record.policy_fingerprint != content.policy_snapshot_digest
        ):
            raise ValueError("content policy snapshot does not match Action Case")
        if (
            record.state_fingerprint is not None
            and record.state_fingerprint != content.content_snapshot_digest
        ):
            raise ValueError("content snapshot does not match Action Case state")
        return self

    @property
    def is_observation(self) -> bool:
        return self.content.operation.effect is ContentEffect.OBSERVATION

    @property
    def requires_mutation_clearance(self) -> bool:
        return self.content.operation.requires_mutation_clearance

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "action_case_ref": {
                "case_id": self.action_case.case_id,
                "tenant_id": self.action_case.tenant_id,
                "case_hash": self.action_case.case_hash,
                "record_version": self.action_case.record_version,
            },
            "content": self.content.canonical_payload(),
        }

    def digest(self) -> str:
        return _digest(self.canonical_payload())

    def target_digest(self) -> str:
        return self.content.target_digest()

    def state_binding_digest(self) -> str:
        return self.content.state_binding_digest()
