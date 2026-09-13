"""Fail-closed binding of admitted state evidence to a workspace projection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .contracts import GovernedWorkspaceContract, canonical_digest

AdmissionDecision = Literal["ADMITTED", "CANDIDATE", "REJECTED"]
_FORBIDDEN_PREFIXES = (
    "reasoning:",
    "chain-of-thought:",
    "cot:",
    "rationale:",
    "reflection:",
    "filler-token:",
    "filler-tokens:",
    "confidence:",
    "self-reported-confidence:",
    "hidden-reasoning:",
    "memory:candidate:",
    "memory:stale:",
    "memory:conflicting:",
    "memory:conflict:",
)


def _digest(value: str, label: str) -> None:
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{label} must be a sha256 digest")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be a sha256 digest") from exc


def _refs(values: tuple[str, ...], label: str) -> None:
    if any(not value.strip() for value in values) or len(set(values)) != len(values):
        raise ValueError(f"{label} must contain unique non-blank values")
    for value in values:
        normalized = value.strip().lower().replace("_", "-")
        if normalized.startswith(_FORBIDDEN_PREFIXES):
            raise ValueError(f"non-authoritative reference cannot satisfy {label}")
        if label == "authority_refs" and normalized.startswith("memory:"):
            raise ValueError("memory cannot satisfy authority_refs")


class StateAdmissionEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    spec_version: Literal["valo.state-admission-evidence/v1"] = (
        "valo.state-admission-evidence/v1"
    )
    admission_id: str = Field(min_length=1)
    state_ref: str = Field(min_length=1)
    state_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    decision: AdmissionDecision
    provenance_refs: tuple[str, ...] = Field(min_length=1)
    authority_refs: tuple[str, ...] = Field(min_length=1)
    evidence_refs: tuple[str, ...] = ()
    admission_policy_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    issuer_id: str = Field(min_length=1)
    evaluated_at: datetime
    valid_until: datetime

    @model_validator(mode="after")
    def validate_evidence(self) -> "StateAdmissionEvidence":
        for label, values in (
            ("provenance_refs", self.provenance_refs),
            ("authority_refs", self.authority_refs),
            ("evidence_refs", self.evidence_refs),
        ):
            _refs(values, label)
        if self.evaluated_at.tzinfo is None or self.valid_until.tzinfo is None:
            raise ValueError("state admission timestamps must be timezone-aware")
        if self.valid_until <= self.evaluated_at:
            raise ValueError("valid_until must follow evaluated_at")
        return self

    def digest(self) -> str:
        return canonical_digest(self.model_dump(mode="json"))


class StateAdmissionSet(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    spec_version: Literal["valo.state-admission-set/v1"] = "valo.state-admission-set/v1"
    admission_set_id: str = Field(min_length=1)
    entries: tuple[StateAdmissionEvidence, ...] = Field(min_length=1)
    issued_at: datetime
    issuer_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_set(self) -> "StateAdmissionSet":
        if self.issued_at.tzinfo is None:
            raise ValueError("issued_at must be timezone-aware")
        if len({entry.state_ref for entry in self.entries}) != len(self.entries):
            raise ValueError("state admission set must contain unique state refs")
        if len({entry.admission_id for entry in self.entries}) != len(self.entries):
            raise ValueError("state admission set must contain unique admission ids")
        return self

    def entry(self, state_ref: str) -> StateAdmissionEvidence | None:
        return next(
            (entry for entry in self.entries if entry.state_ref == state_ref), None
        )

    def digest_for(self, state_refs: tuple[str, ...]) -> str:
        selected = []
        for state_ref in sorted(state_refs):
            entry = self.entry(state_ref)
            if entry is None:
                raise ValueError(f"missing state admission evidence for {state_ref!r}")
            selected.append(entry.digest())
        return canonical_digest(
            {
                "spec_version": "valo.selected-state-admission-set/v1",
                "state_refs": sorted(state_refs),
                "entry_digests": selected,
            }
        )


class WorkspaceStateAdmissionBinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    spec_version: Literal["valo.workspace-state-admission-binding/v1"] = (
        "valo.workspace-state-admission-binding/v1"
    )
    workspace_contract_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    admission_set_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    governed_state_refs: tuple[str, ...] = Field(min_length=1)
    state_evidence_digests: tuple[str, ...] = Field(min_length=1)
    bound_at: datetime
    valid_until: datetime

    @model_validator(mode="after")
    def validate_binding(self) -> "WorkspaceStateAdmissionBinding":
        _refs(self.governed_state_refs, "governed_state_refs")
        for digest in self.state_evidence_digests:
            _digest(digest, "state_evidence_digest")
        if len(self.governed_state_refs) != len(self.state_evidence_digests):
            raise ValueError(
                "state refs and evidence digests must have identical cardinality"
            )
        if (
            self.bound_at.tzinfo is None
            or self.valid_until.tzinfo is None
            or self.valid_until <= self.bound_at
        ):
            raise ValueError("workspace state admission timestamps are invalid")
        return self

    def digest(self) -> str:
        return canonical_digest(self.model_dump(mode="json"))


@dataclass(frozen=True)
class StateAdmissionConformanceResult:
    conformant: bool
    violations: tuple[str, ...]


def _violations(
    contract: GovernedWorkspaceContract, admissions: StateAdmissionSet, at: datetime
) -> list[str]:
    if at.tzinfo is None:
        raise ValueError("admission verification time must be timezone-aware")
    violations: list[str] = []
    if not contract.governed_state_refs:
        violations.append("governed_state_refs_empty")
    if at < contract.valid_from:
        violations.append("workspace_contract_not_yet_valid")
    if at >= contract.valid_until:
        violations.append("workspace_contract_expired")
    for state_ref in contract.governed_state_refs:
        entry = admissions.entry(state_ref)
        if entry is None:
            violations.append(f"state_admission_missing:{state_ref}")
            continue
        if entry.decision != "ADMITTED":
            violations.append(f"state_not_admitted:{state_ref}:{entry.decision}")
        if entry.evaluated_at > at:
            violations.append(f"state_admission_from_future:{state_ref}")
        if at >= entry.valid_until:
            violations.append(f"state_admission_expired:{state_ref}")
        if not set(entry.provenance_refs).issubset(contract.provenance_refs):
            violations.append(f"state_provenance_not_projected:{state_ref}")
    return violations


def verify_workspace_state_admission(
    contract: GovernedWorkspaceContract,
    admissions: StateAdmissionSet,
    *,
    at: datetime | None = None,
) -> StateAdmissionConformanceResult:
    violations = _violations(contract, admissions, at or datetime.now(timezone.utc))
    return StateAdmissionConformanceResult(not violations, tuple(violations))


def bind_workspace_state_admission(
    contract: GovernedWorkspaceContract,
    admissions: StateAdmissionSet,
    *,
    bound_at: datetime,
) -> WorkspaceStateAdmissionBinding:
    violations = _violations(contract, admissions, bound_at)
    if violations:
        raise ValueError("workspace state admission failed: " + ",".join(violations))
    refs = tuple(sorted(contract.governed_state_refs))
    entries = [admissions.entry(ref) for ref in refs]
    if any(entry is None for entry in entries):
        raise ValueError("workspace state admission evidence is incomplete")
    concrete = [entry for entry in entries if entry is not None]
    return WorkspaceStateAdmissionBinding(
        workspace_contract_digest=canonical_digest(contract),
        admission_set_digest=admissions.digest_for(refs),
        governed_state_refs=refs,
        state_evidence_digests=tuple(entry.digest() for entry in concrete),
        bound_at=bound_at,
        valid_until=min(
            contract.valid_until, *(entry.valid_until for entry in concrete)
        ),
    )
