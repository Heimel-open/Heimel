from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import canonical_digest


class DependencyDomain(StrEnum):
    PHYSICAL_PATH = "PHYSICAL_PATH"
    PROVIDER = "PROVIDER"
    JURISDICTION = "JURISDICTION"
    AUTHORITY_SOURCE = "AUTHORITY_SOURCE"
    CREDENTIAL_CONTROL_PLANE = "CREDENTIAL_CONTROL_PLANE"
    EXECUTION_PEP = "EXECUTION_PEP"
    RECOVERY_PATH = "RECOVERY_PATH"


class DependencyEvidenceStatus(StrEnum):
    VERIFIED = "VERIFIED"
    UNKNOWN = "UNKNOWN"
    STALE = "STALE"
    CONFLICTED = "CONFLICTED"
    REVOKED = "REVOKED"


class DiversityDisposition(StrEnum):
    INDEPENDENT = "INDEPENDENT"
    CONCENTRATED = "CONCENTRATED"
    INDETERMINATE = "INDETERMINATE"


class ConcentrationBasis(StrEnum):
    DEPENDENCY = "DEPENDENCY"
    CONTROLLER = "CONTROLLER"


class DependencyReference(BaseModel):
    schema_version: Literal["dependency_reference.v1"] = "dependency_reference.v1"
    domain: DependencyDomain
    dependency_id: str
    controller_ref: str
    evidence_ref: str
    evidence_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    observed_at: datetime
    valid_until: datetime
    status: DependencyEvidenceStatus
    reference_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    @property
    def ref(self) -> str:
        return f"{self.domain.value}:{self.dependency_id}:{self.controller_ref}"

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"reference_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_reference(self) -> DependencyReference:
        if not self.dependency_id or not self.controller_ref or not self.evidence_ref:
            raise ValueError("dependency identity, controller and evidence are required")
        if self.valid_until <= self.observed_at:
            raise ValueError("dependency evidence must expire after observation")
        if self.reference_digest and self.reference_digest != self.computed_digest:
            raise ValueError("dependency reference digest mismatch")
        return self


class RouteDependencyTopology(BaseModel):
    schema_version: Literal["route_dependency_topology.v1"] = (
        "route_dependency_topology.v1"
    )
    route_id: str
    dependencies: tuple[DependencyReference, ...]
    complete_domains: tuple[DependencyDomain, ...]
    topology_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"topology_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_topology(self) -> RouteDependencyTopology:
        if not self.route_id:
            raise ValueError("route_id is required")
        if not self.dependencies:
            raise ValueError("route topology requires dependencies")
        refs = [item.ref for item in self.dependencies]
        if len(set(refs)) != len(refs):
            raise ValueError("route dependencies must be unique")
        if tuple(sorted(refs)) != tuple(refs):
            raise ValueError("route dependencies must be sorted")
        if not self.complete_domains:
            raise ValueError("route topology requires explicit complete domains")
        domain_values = [item.value for item in self.complete_domains]
        if len(set(domain_values)) != len(domain_values):
            raise ValueError("complete dependency domains must be unique")
        if tuple(sorted(domain_values)) != tuple(domain_values):
            raise ValueError("complete dependency domains must be sorted")
        present_domains = {item.domain for item in self.dependencies}
        if not set(self.complete_domains).issubset(present_domains):
            raise ValueError("a complete domain must contain dependency evidence")
        for item in self.dependencies:
            if not item.reference_digest or item.reference_digest != item.computed_digest:
                raise ValueError("route topology contains unsealed dependency evidence")
        if self.topology_digest and self.topology_digest != self.computed_digest:
            raise ValueError("route dependency topology digest mismatch")
        return self


class ConcentrationFinding(BaseModel):
    basis: ConcentrationBasis
    domain: DependencyDomain
    shared_ref: str
    route_ids: tuple[str, ...]

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_finding(self) -> ConcentrationFinding:
        if not self.shared_ref:
            raise ValueError("shared concentration reference is required")
        if len(self.route_ids) < 2:
            raise ValueError("concentration requires at least two affected routes")
        if len(set(self.route_ids)) != len(self.route_ids):
            raise ValueError("concentration route ids must be unique")
        if tuple(sorted(self.route_ids)) != self.route_ids:
            raise ValueError("concentration route ids must be sorted")
        return self


class DependencyDiversityReport(BaseModel):
    schema_version: Literal["dependency_diversity_report.v1"] = (
        "dependency_diversity_report.v1"
    )
    topology_digests: tuple[str, ...]
    required_domains: tuple[DependencyDomain, ...]
    evaluated_at: datetime
    disposition: DiversityDisposition
    independent: bool
    findings: tuple[ConcentrationFinding, ...] = ()
    incomplete_domains: tuple[str, ...] = ()
    max_concentration_bps: int = Field(ge=0, le=10000)
    reasons: tuple[str, ...] = ()
    report_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"report_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_report(self) -> DependencyDiversityReport:
        if len(set(self.topology_digests)) != len(self.topology_digests):
            raise ValueError("topology digests must be unique")
        if tuple(sorted(self.topology_digests)) != self.topology_digests:
            raise ValueError("topology digests must be sorted")
        domain_values = [item.value for item in self.required_domains]
        if not domain_values or len(set(domain_values)) != len(domain_values):
            raise ValueError("required dependency domains must be non-empty and unique")
        if tuple(sorted(domain_values)) != tuple(domain_values):
            raise ValueError("required dependency domains must be sorted")
        if self.independent != (self.disposition is DiversityDisposition.INDEPENDENT):
            raise ValueError("independent flag must match diversity disposition")
        if self.disposition is DiversityDisposition.INDEPENDENT:
            if self.findings or self.incomplete_domains or self.reasons:
                raise ValueError("independent result cannot contain risk findings")
        elif not self.reasons:
            raise ValueError("non-independent result requires reasons")
        if len(set(self.incomplete_domains)) != len(self.incomplete_domains):
            raise ValueError("incomplete domain references must be unique")
        if tuple(sorted(self.incomplete_domains)) != self.incomplete_domains:
            raise ValueError("incomplete domain references must be sorted")
        if len(set(self.reasons)) != len(self.reasons):
            raise ValueError("dependency diversity reasons must be unique")
        if tuple(sorted(self.reasons)) != self.reasons:
            raise ValueError("dependency diversity reasons must be sorted")
        if self.report_digest and self.report_digest != self.computed_digest:
            raise ValueError("dependency diversity report digest mismatch")
        return self


def seal_dependency_reference(**values: object) -> DependencyReference:
    provisional = DependencyReference.model_validate(values)
    return DependencyReference.model_validate(
        {
            **provisional.model_dump(mode="python"),
            "reference_digest": provisional.computed_digest,
        }
    )


def seal_route_dependency_topology(
    *,
    route_id: str,
    dependencies: tuple[DependencyReference, ...],
    complete_domains: tuple[DependencyDomain, ...],
) -> RouteDependencyTopology:
    sorted_dependencies = tuple(sorted(dependencies, key=lambda item: item.ref))
    sorted_domains = tuple(sorted(complete_domains, key=lambda item: item.value))
    provisional = RouteDependencyTopology(
        route_id=route_id,
        dependencies=sorted_dependencies,
        complete_domains=sorted_domains,
    )
    return RouteDependencyTopology.model_validate(
        {
            **provisional.model_dump(mode="python"),
            "topology_digest": provisional.computed_digest,
        }
    )
