from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .common import canonical_digest


class VerificationMethod(str, Enum):
    REFERENCE = "REFERENCE"
    INDEPENDENT_ROUTE = "INDEPENDENT_ROUTE"
    EXPECTED_REFUSAL = "EXPECTED_REFUSAL"


class VerificationCheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class VerificationProofOutcome(str, Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"


class RegenerationOutcome(str, Enum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"


def _sorted_unique(values: tuple[str, ...], label: str) -> tuple[str, ...]:
    if any(not value.strip() for value in values):
        raise ValueError(f"{label} cannot contain blank references")
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")
    return tuple(sorted(values))


def _normalize_digest_refs(values: tuple[str, ...], label: str) -> tuple[str, ...]:
    normalized = _sorted_unique(values, label)
    if any(
        len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
        for value in normalized
    ):
        raise ValueError(f"{label} must contain sha256 hex digests")
    return normalized


class VerificationCheckResult(BaseModel):
    schema_version: Literal["kernel_verification_check.v1"] = (
        "kernel_verification_check.v1"
    )
    check_id: str = Field(min_length=1)
    method: VerificationMethod
    status: VerificationCheckStatus
    required: bool = True
    basis_refs: tuple[str, ...] = Field(min_length=1)
    evidence_refs: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    refusal_expected: bool | None = None
    refusal_observed: bool | None = None
    check_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("basis_refs", "evidence_refs", "reason_codes")
    @classmethod
    def normalize_refs(cls, values: tuple[str, ...], info) -> tuple[str, ...]:
        return _sorted_unique(values, info.field_name)

    @model_validator(mode="after")
    def validate_check(self) -> VerificationCheckResult:
        if self.status == VerificationCheckStatus.PASS and not self.evidence_refs:
            raise ValueError("PASS verification check requires evidence")
        if self.status == VerificationCheckStatus.FAIL and not self.reason_codes:
            raise ValueError("FAIL verification check requires reason_codes")
        if self.method == VerificationMethod.EXPECTED_REFUSAL:
            if self.refusal_expected is not True:
                raise ValueError("EXPECTED_REFUSAL requires refusal_expected=True")
            if self.refusal_observed is None:
                raise ValueError("EXPECTED_REFUSAL requires refusal_observed")
            expected_status = (
                VerificationCheckStatus.PASS
                if self.refusal_observed
                else VerificationCheckStatus.FAIL
            )
            if self.status != expected_status:
                raise ValueError(
                    "EXPECTED_REFUSAL status must PASS only when refusal is observed"
                )
        elif self.refusal_expected is not None or self.refusal_observed is not None:
            raise ValueError("refusal fields are valid only for EXPECTED_REFUSAL")
        payload = self.model_dump(mode="python", exclude={"check_digest"})
        if canonical_digest(payload) != self.check_digest:
            raise ValueError("verification check digest mismatch")
        return self


class VerificationStepAnchor(BaseModel):
    schema_version: Literal["kernel_verification_step_anchor.v1"] = (
        "kernel_verification_step_anchor.v1"
    )
    step_id: str = Field(min_length=1)
    subject_ref: str = Field(min_length=1)
    definition_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    input_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    output_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    check_digests: tuple[str, ...] = Field(min_length=1)
    ledger_anchor_ref: str = Field(min_length=1)
    previous_step_digest: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    step_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("check_digests")
    @classmethod
    def normalize_check_digests(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _normalize_digest_refs(values, "check_digests")

    @model_validator(mode="after")
    def validate_anchor(self) -> VerificationStepAnchor:
        payload = self.model_dump(mode="python", exclude={"step_digest"})
        if canonical_digest(payload) != self.step_digest:
            raise ValueError("verification step digest mismatch")
        return self


class VerificationProof(BaseModel):
    schema_version: Literal["kernel_verification_proof.v1"] = (
        "kernel_verification_proof.v1"
    )
    proof_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    subject_ref: str = Field(min_length=1)
    version_ref: str = Field(min_length=1)
    definition_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    input_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    output_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    required_methods: tuple[VerificationMethod, ...] = Field(min_length=1)
    checks: tuple[VerificationCheckResult, ...] = Field(min_length=1)
    step_anchors: tuple[VerificationStepAnchor, ...] = Field(min_length=1)
    created_at: datetime
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    can_execute: Literal[False] = False
    reproduction_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    proof_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("required_methods")
    @classmethod
    def normalize_methods(
        cls, values: tuple[VerificationMethod, ...]
    ) -> tuple[VerificationMethod, ...]:
        if len(values) != len(set(values)):
            raise ValueError("required_methods must be unique")
        return tuple(sorted(values, key=lambda item: item.value))

    @model_validator(mode="after")
    def validate_proof(self) -> VerificationProof:
        check_ids = tuple(check.check_id for check in self.checks)
        if len(check_ids) != len(set(check_ids)):
            raise ValueError("verification check ids must be unique")

        check_digests = {check.check_digest for check in self.checks}
        if len(check_digests) != len(self.checks):
            raise ValueError("verification check digests must be unique")

        step_ids = tuple(step.step_id for step in self.step_anchors)
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("verification step ids must be unique")

        seen_step_digests: set[str] = set()
        previous_digest: str | None = None
        previous_output: str | None = None

        for index, step in enumerate(self.step_anchors):
            if step.subject_ref != self.subject_ref:
                raise ValueError("verification step subject mismatch")
            if step.definition_digest != self.definition_digest:
                raise ValueError("verification step definition mismatch")
            if step.previous_step_digest != previous_digest:
                raise ValueError("verification step chain mismatch")
            if index == 0 and step.input_digest != self.input_digest:
                raise ValueError("first verification step input mismatch")
            if previous_output is not None and step.input_digest != previous_output:
                raise ValueError("verification step input/output chain mismatch")
            if set(step.check_digests) - check_digests:
                raise ValueError("verification step references unknown check digest")
            if step.step_digest in seen_step_digests:
                raise ValueError("verification step digests must be unique")
            seen_step_digests.add(step.step_digest)
            previous_digest = step.step_digest
            previous_output = step.output_digest

        if self.step_anchors[-1].output_digest != self.output_digest:
            raise ValueError("final verification step output mismatch")

        covered = {
            digest for step in self.step_anchors for digest in step.check_digests
        }
        if covered != check_digests:
            raise ValueError("every verification check must be anchored to a step")

        if canonical_digest(_reproduction_payload(self)) != self.reproduction_digest:
            raise ValueError("verification reproduction digest mismatch")

        payload = self.model_dump(mode="python", exclude={"proof_digest"})
        if canonical_digest(payload) != self.proof_digest:
            raise ValueError("verification proof digest mismatch")
        return self


class VerificationProofAssessment(BaseModel):
    schema_version: Literal["kernel_verification_proof_assessment.v1"] = (
        "kernel_verification_proof_assessment.v1"
    )
    proof_id: str
    outcome: VerificationProofOutcome
    blocking_check_ids: tuple[str, ...] = ()
    missing_methods: tuple[VerificationMethod, ...] = ()
    reason_codes: tuple[str, ...] = ()
    can_rely_on_verification: bool
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    can_execute: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)


class RegenerationAssessment(BaseModel):
    schema_version: Literal["kernel_verification_regeneration_assessment.v1"] = (
        "kernel_verification_regeneration_assessment.v1"
    )
    first_proof_id: str
    second_proof_id: str
    outcome: RegenerationOutcome
    matching_reproduction_digest: bool
    reason_codes: tuple[str, ...] = ()

    model_config = ConfigDict(extra="forbid", frozen=True)


def _reproduction_payload(proof: VerificationProof) -> dict:
    return {
        "schema_version": proof.schema_version,
        "tenant_id": proof.tenant_id,
        "subject_ref": proof.subject_ref,
        "version_ref": proof.version_ref,
        "definition_digest": proof.definition_digest,
        "input_digest": proof.input_digest,
        "output_digest": proof.output_digest,
        "required_methods": tuple(method.value for method in proof.required_methods),
        "checks": tuple(
            check.model_dump(mode="python", exclude={"check_digest"})
            for check in proof.checks
        ),
        "steps": tuple(
            {
                "subject_ref": step.subject_ref,
                "definition_digest": step.definition_digest,
                "input_digest": step.input_digest,
                "output_digest": step.output_digest,
                "check_digests": step.check_digests,
            }
            for step in proof.step_anchors
        ),
    }


def _reproduction_payload_from_parts(
    *,
    tenant_id: str,
    subject_ref: str,
    version_ref: str,
    definition_digest: str,
    input_digest: str,
    output_digest: str,
    required_methods: tuple[VerificationMethod, ...],
    checks: tuple[VerificationCheckResult, ...],
    step_anchors: tuple[VerificationStepAnchor, ...],
) -> dict:
    return {
        "schema_version": "kernel_verification_proof.v1",
        "tenant_id": tenant_id,
        "subject_ref": subject_ref,
        "version_ref": version_ref,
        "definition_digest": definition_digest,
        "input_digest": input_digest,
        "output_digest": output_digest,
        "required_methods": tuple(method.value for method in required_methods),
        "checks": tuple(
            check.model_dump(mode="python", exclude={"check_digest"})
            for check in checks
        ),
        "steps": tuple(
            {
                "subject_ref": step.subject_ref,
                "definition_digest": step.definition_digest,
                "input_digest": step.input_digest,
                "output_digest": step.output_digest,
                "check_digests": step.check_digests,
            }
            for step in step_anchors
        ),
    }


def seal_verification_check(**values) -> VerificationCheckResult:
    payload = {
        "schema_version": "kernel_verification_check.v1",
        "required": True,
        "evidence_refs": (),
        "reason_codes": (),
        "refusal_expected": None,
        "refusal_observed": None,
        **values,
    }
    for field in ("basis_refs", "evidence_refs", "reason_codes"):
        payload[field] = _sorted_unique(tuple(payload[field]), field)
    return VerificationCheckResult(
        **payload,
        check_digest=canonical_digest(payload),
    )


def seal_verification_step_anchor(**values) -> VerificationStepAnchor:
    payload = {
        "schema_version": "kernel_verification_step_anchor.v1",
        "previous_step_digest": None,
        **values,
    }
    payload["check_digests"] = _normalize_digest_refs(
        tuple(payload["check_digests"]), "check_digests"
    )
    return VerificationStepAnchor(
        **payload,
        step_digest=canonical_digest(payload),
    )


def seal_verification_proof(**values) -> VerificationProof:
    payload = {
        "schema_version": "kernel_verification_proof.v1",
        "authority_effect": "NO_AUTHORITY_CREATION",
        "can_issue_clearance": False,
        "can_execute": False,
        **values,
    }
    checks = tuple(
        item
        if isinstance(item, VerificationCheckResult)
        else VerificationCheckResult.model_validate(item)
        for item in payload["checks"]
    )
    checks = tuple(sorted(checks, key=lambda item: item.check_id))
    step_anchors = tuple(
        item
        if isinstance(item, VerificationStepAnchor)
        else VerificationStepAnchor.model_validate(item)
        for item in payload["step_anchors"]
    )
    required_methods = tuple(
        item if isinstance(item, VerificationMethod) else VerificationMethod(item)
        for item in payload["required_methods"]
    )
    if len(required_methods) != len(set(required_methods)):
        raise ValueError("required_methods must be unique")
    required_methods = tuple(sorted(required_methods, key=lambda item: item.value))

    payload["required_methods"] = required_methods
    payload["checks"] = checks
    payload["step_anchors"] = step_anchors
    reproduction_payload = _reproduction_payload_from_parts(
        tenant_id=payload["tenant_id"],
        subject_ref=payload["subject_ref"],
        version_ref=payload["version_ref"],
        definition_digest=payload["definition_digest"],
        input_digest=payload["input_digest"],
        output_digest=payload["output_digest"],
        required_methods=required_methods,
        checks=checks,
        step_anchors=step_anchors,
    )
    payload["reproduction_digest"] = canonical_digest(reproduction_payload)
    digest_payload = {
        **payload,
        "checks": tuple(item.model_dump(mode="python") for item in checks),
        "step_anchors": tuple(
            item.model_dump(mode="python") for item in step_anchors
        ),
    }
    return VerificationProof(
        **digest_payload,
        proof_digest=canonical_digest(digest_payload),
    )


def assess_verification_proof(
    proof: VerificationProof,
) -> VerificationProofAssessment:
    blocking = tuple(
        sorted(
            check.check_id
            for check in proof.checks
            if check.required and check.status != VerificationCheckStatus.PASS
        )
    )
    passing_methods = {
        check.method
        for check in proof.checks
        if check.status == VerificationCheckStatus.PASS
    }
    missing_methods = tuple(
        method for method in proof.required_methods if method not in passing_methods
    )
    reasons: list[str] = []
    if blocking:
        reasons.append("REQUIRED_CHECK_NOT_PASS")
    if missing_methods:
        reasons.append("REQUIRED_METHOD_MISSING")
    outcome = (
        VerificationProofOutcome.COMPLETE
        if not reasons
        else VerificationProofOutcome.INCOMPLETE
    )
    return VerificationProofAssessment(
        proof_id=proof.proof_id,
        outcome=outcome,
        blocking_check_ids=blocking,
        missing_methods=missing_methods,
        reason_codes=tuple(sorted(reasons)),
        can_rely_on_verification=outcome == VerificationProofOutcome.COMPLETE,
    )


def assess_regeneration(
    first: VerificationProof,
    second: VerificationProof,
) -> RegenerationAssessment:
    match = first.reproduction_digest == second.reproduction_digest
    return RegenerationAssessment(
        first_proof_id=first.proof_id,
        second_proof_id=second.proof_id,
        outcome=(
            RegenerationOutcome.MATCH if match else RegenerationOutcome.MISMATCH
        ),
        matching_reproduction_digest=match,
        reason_codes=() if match else ("REPRODUCTION_DIGEST_MISMATCH",),
    )
