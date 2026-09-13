"""Context and consent gateway for Advisor Fabric.

This module defines the boundary that future OLAV, memory and product adapters
must use before an advisor receives context. It is intentionally in-memory and
side-effect free for now: callers provide scoped refs, and the gateway validates
them against an AdvisorProfile.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .profiles import get_advisor_profile
from .schemas import AdvisorAuthorityBoundary, AdvisorMemoryPolicy, AdvisorProfile


class AdvisorConsentBasis(str, Enum):
    """Consent or lawful-basis vocabulary allowed into Advisor Fabric."""

    PUBLIC = "public"
    CUSTOMER_CONSENT = "customer_consent"
    PRODUCT_TOS = "product_tos"
    PRODUCT_TELEMETRY = "product_telemetry"
    INTERNAL_OPERATIONAL = "internal_operational"
    CONTRACTUAL = "contractual"


class AdvisorContextScope(str, Enum):
    """Scope of a context reference."""

    PUBLIC = "public"
    TENANT = "tenant"
    USER = "user"
    SESSION = "session"


class AdvisorContextRef(BaseModel):
    """Reference to source context made available to an advisor."""

    ref_id: str
    source_type: str
    scope: AdvisorContextScope
    consent_basis: AdvisorConsentBasis
    source_ref: str
    evidence_refs: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(use_enum_values=False)


class AdvisorMemoryRef(BaseModel):
    """Reference to memory made available through the gateway."""

    ref_id: str
    scope: AdvisorContextScope
    memory_policy: AdvisorMemoryPolicy
    source_ref: str
    evidence_refs: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(use_enum_values=False)

    @model_validator(mode="after")
    def _tenant_memory_must_not_be_public(self) -> "AdvisorMemoryRef":
        if self.memory_policy == AdvisorMemoryPolicy.TENANT_SCOPED and self.scope == AdvisorContextScope.PUBLIC:
            raise ValueError("tenant-scoped memory cannot use public scope")
        return self


class AdvisorContextPackage(BaseModel):
    """Validated context package delivered to an advisor."""

    package_id: str
    advisor_id: str
    role: str
    context_refs: Tuple[AdvisorContextRef, ...] = Field(default_factory=tuple)
    memory_refs: Tuple[AdvisorMemoryRef, ...] = Field(default_factory=tuple)
    limitations: Tuple[str, ...] = Field(default_factory=tuple)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    authority_boundary: AdvisorAuthorityBoundary = AdvisorAuthorityBoundary.ADVISORY_ONLY

    model_config = ConfigDict(use_enum_values=False)


class AdvisorContextGateway:
    """Validate and package context for one Advisor profile."""

    def __init__(self, profiles: Optional[Mapping[str, AdvisorProfile]] = None):
        self._profiles = profiles

    def build_package(
        self,
        *,
        package_id: str,
        role: str,
        context_refs: Iterable[AdvisorContextRef],
        memory_refs: Iterable[AdvisorMemoryRef] = (),
        limitations: Iterable[str] = (),
    ) -> AdvisorContextPackage:
        profile = self._get_profile(role)
        context_tuple = tuple(context_refs)
        memory_tuple = tuple(memory_refs)
        self._validate_context_refs(profile, context_tuple)
        self._validate_memory_refs(profile, memory_tuple)

        return AdvisorContextPackage(
            package_id=package_id,
            advisor_id=profile.advisor_id,
            role=profile.role,
            context_refs=context_tuple,
            memory_refs=memory_tuple,
            limitations=tuple(limitations),
        )

    def _get_profile(self, role: str) -> AdvisorProfile:
        if self._profiles is None:
            return get_advisor_profile(role)
        try:
            return self._profiles[role]
        except KeyError as exc:
            raise KeyError(f"unknown advisor role: {role}") from exc

    @staticmethod
    def _validate_context_refs(
        profile: AdvisorProfile,
        context_refs: Tuple[AdvisorContextRef, ...],
    ) -> None:
        allowed_inputs = set(profile.allowed_inputs)
        invalid = sorted({ref.source_type for ref in context_refs if ref.source_type not in allowed_inputs})
        if invalid:
            raise ValueError(f"context source not allowed for {profile.role}: {', '.join(invalid)}")

        missing_evidence = sorted(ref.ref_id for ref in context_refs if not ref.evidence_refs)
        if missing_evidence:
            raise ValueError(f"context refs require evidence refs: {', '.join(missing_evidence)}")

    @staticmethod
    def _validate_memory_refs(
        profile: AdvisorProfile,
        memory_refs: Tuple[AdvisorMemoryRef, ...],
    ) -> None:
        if profile.memory_policy == AdvisorMemoryPolicy.NONE and memory_refs:
            raise ValueError(f"{profile.role} does not allow memory refs")

        invalid_policy = sorted(
            ref.ref_id for ref in memory_refs if ref.memory_policy != profile.memory_policy
        )
        if invalid_policy:
            raise ValueError(f"memory refs violate profile memory policy: {', '.join(invalid_policy)}")
