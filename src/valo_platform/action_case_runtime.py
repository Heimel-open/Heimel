from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .memory_provider import canonical_digest


class CaseRuntimeError(RuntimeError):
    pass


class ConcurrencyConflict(CaseRuntimeError):
    pass


class CorruptCase(CaseRuntimeError):
    pass


class CaseCondition(str, Enum):
    ACTIVE = "active"
    RECOVERED_REVALIDATION_REQUIRED = "recovered_revalidation_required"
    INCOMPLETE_EXECUTION = "incomplete_execution"
    UNRESOLVED_OUTCOME = "unresolved_outcome"
    TERMINAL = "terminal"
    QUARANTINED = "quarantined"


TERMINAL_STATES = frozenset({"CLOSED", "DENIED", "HALTED"})
EXECUTION_STATES = frozenset({"EXECUTING", "EXECUTED"})
OUTCOME_PENDING_STATES = frozenset({"OUTCOME_RECORDED", "ASSESSED", "REMEDIATION_PROPOSED"})


class StoredTransition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0"
    case_id: str = Field(min_length=1)
    action_ref: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    previous_receipt_digest: str | None = None
    previous_state: str = Field(min_length=1)
    next_state: str = Field(min_length=1)
    artifact_type: str = Field(min_length=1)
    artifact_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    actor_id: str = Field(min_length=1)
    principal_id: str = Field(min_length=1)
    occurred_at: datetime
    idempotency_key: str = Field(min_length=1)
    receipt_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_digest(self) -> "StoredTransition":
        if self.receipt_digest != transition_digest(self):
            raise ValueError("receipt_digest does not match canonical transition payload")
        if self.sequence == 1 and self.previous_receipt_digest is not None:
            raise ValueError("first transition cannot have previous receipt digest")
        if self.sequence > 1 and self.previous_receipt_digest is None:
            raise ValueError("non-first transition requires previous receipt digest")
        return self


class RegisteredCase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0"
    case_id: str = Field(min_length=1)
    action_ref: str = Field(min_length=1)
    principal_id: str = Field(min_length=1)
    initial_state: str = Field(min_length=1)
    case_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    registered_at: datetime
    linked_parent_case_id: str | None = None
    grants_authority: bool = False

    @model_validator(mode="after")
    def enforce_boundary(self) -> "RegisteredCase":
        if self.grants_authority:
            raise ValueError("case registration cannot grant authority")
        expected = canonical_digest(self.model_dump(mode="json", exclude={"case_digest"}))
        if self.case_digest != expected:
            raise ValueError("case_digest mismatch")
        return self


class RecoveredCase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    action_ref: str
    principal_id: str
    current_state: str
    sequence: int
    last_receipt_digest: str | None
    artifact_index: tuple[tuple[str, str], ...]
    linked_remediation_cases: tuple[str, ...]
    condition: CaseCondition
    errors: tuple[str, ...] = ()
    automatic_continuation_allowed: bool = False
    revalidation_required: bool = True

    @model_validator(mode="after")
    def recovery_never_authorizes(self) -> "RecoveredCase":
        if self.automatic_continuation_allowed:
            raise ValueError("recovery cannot automatically continue execution")
        return self


class VerificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    valid: bool
    condition: CaseCondition
    receipt_count: int
    chain_digest: str
    errors: tuple[str, ...] = ()
    grants_authority: bool = False


class EvidencePackage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0"
    case: RegisteredCase
    transitions: tuple[StoredTransition, ...]
    artifact_linkage: tuple[tuple[str, str], ...]
    linked_remediation_cases: tuple[str, ...]
    unresolved_effects: tuple[str, ...]
    dissent: tuple[str, ...]
    verification: VerificationResult
    lifecycle_trace: tuple[str, ...]
    package_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def package_is_canonical(self) -> "EvidencePackage":
        if self.package_digest != evidence_package_digest(self):
            raise ValueError("package_digest mismatch")
        return self


class AppendLog(Protocol):
    def append(self, case_id: str, record: dict[str, Any]) -> None: ...
    def read(self, case_id: str) -> tuple[dict[str, Any], ...]: ...


class InMemoryAppendLog:
    def __init__(self) -> None:
        self._records: dict[str, list[dict[str, Any]]] = {}

    def append(self, case_id: str, record: dict[str, Any]) -> None:
        self._records.setdefault(case_id, []).append(dict(record))

    def read(self, case_id: str) -> tuple[dict[str, Any], ...]:
        return tuple(dict(item) for item in self._records.get(case_id, ()))


def transition_digest(transition: StoredTransition) -> str:
    return canonical_digest(transition.model_dump(mode="json", exclude={"receipt_digest"}))


def evidence_package_digest(package: EvidencePackage) -> str:
    return canonical_digest(package.model_dump(mode="json", exclude={"package_digest"}))


def build_registered_case(
    *, case_id: str, action_ref: str, principal_id: str, initial_state: str = "PROPOSED",
    registered_at: datetime | None = None, linked_parent_case_id: str | None = None,
) -> RegisteredCase:
    payload = {
        "schema_version": "1.0", "case_id": case_id, "action_ref": action_ref,
        "principal_id": principal_id, "initial_state": initial_state,
        "registered_at": registered_at or datetime.now(timezone.utc),
        "linked_parent_case_id": linked_parent_case_id, "grants_authority": False,
    }
    return RegisteredCase(**payload, case_digest=canonical_digest(payload))


def build_transition(
    *, case: RegisteredCase, sequence: int, previous_receipt_digest: str | None,
    previous_state: str, next_state: str, artifact_type: str, artifact_digest: str,
    actor_id: str, idempotency_key: str, occurred_at: datetime | None = None,
) -> StoredTransition:
    payload = {
        "schema_version": "1.0", "case_id": case.case_id, "action_ref": case.action_ref,
        "sequence": sequence, "previous_receipt_digest": previous_receipt_digest,
        "previous_state": previous_state, "next_state": next_state,
        "artifact_type": artifact_type, "artifact_digest": artifact_digest,
        "actor_id": actor_id, "principal_id": case.principal_id,
        "occurred_at": occurred_at or datetime.now(timezone.utc),
        "idempotency_key": idempotency_key,
    }
    provisional = StoredTransition.model_construct(**payload, receipt_digest="sha256:" + "0" * 64)
    return StoredTransition(**payload, receipt_digest=transition_digest(provisional))


@dataclass
class DurableActionCaseStore:
    log: AppendLog

    def register_case(self, case: RegisteredCase, *, idempotency_key: str) -> RegisteredCase:
        records = self.log.read(case.case_id)
        if records:
            first = records[0]
            if first.get("kind") == "case" and first.get("idempotency_key") == idempotency_key:
                existing = RegisteredCase(**first["payload"])
                if existing == case:
                    return existing
            raise ConcurrencyConflict("case already registered")
        self.log.append(case.case_id, {"kind": "case", "idempotency_key": idempotency_key, "payload": case.model_dump(mode="json")})
        return case

    def append_transition(
        self, transition: StoredTransition, *, expected_sequence: int,
        expected_previous_digest: str | None,
    ) -> StoredTransition:
        recovered = self.recover(transition.case_id, fail_on_corruption=True)
        if recovered.condition in {CaseCondition.TERMINAL, CaseCondition.QUARANTINED}:
            raise ConcurrencyConflict("terminal or quarantined case cannot continue")

        records = self.log.read(transition.case_id)
        for record in records:
            if record.get("kind") != "transition":
                continue
            existing = StoredTransition(**record["payload"])
            if existing.idempotency_key == transition.idempotency_key:
                if existing == transition:
                    return existing
                raise ConcurrencyConflict("idempotency key reused with different payload")
            if existing.receipt_digest == transition.receipt_digest:
                raise ConcurrencyConflict("duplicate transition receipt")

        if expected_sequence != recovered.sequence:
            raise ConcurrencyConflict("stale expected sequence")
        if expected_previous_digest != recovered.last_receipt_digest:
            raise ConcurrencyConflict("stale previous receipt digest")
        if transition.sequence != recovered.sequence + 1:
            raise ConcurrencyConflict("transition sequence is not next")
        if transition.previous_receipt_digest != recovered.last_receipt_digest:
            raise ConcurrencyConflict("transition previous digest mismatch")
        if transition.previous_state != recovered.current_state:
            raise ConcurrencyConflict("transition previous state mismatch")
        if transition.action_ref != recovered.action_ref or transition.principal_id != recovered.principal_id:
            raise CorruptCase("cross-case or cross-principal transition injection")

        self.log.append(transition.case_id, {"kind": "transition", "payload": transition.model_dump(mode="json")})
        return transition

    def register_remediation_case(self, parent_case_id: str, remediation: RegisteredCase, *, idempotency_key: str) -> RegisteredCase:
        parent = self.recover(parent_case_id, fail_on_corruption=True)
        if remediation.linked_parent_case_id != parent_case_id:
            raise CorruptCase("remediation case must bind parent case")
        self.register_case(remediation, idempotency_key=idempotency_key)
        self.log.append(parent_case_id, {"kind": "remediation_link", "child_case_id": remediation.case_id})
        return remediation

    def recover(self, case_id: str, *, fail_on_corruption: bool = False) -> RecoveredCase:
        raw = self.log.read(case_id)
        errors: list[str] = []
        if not raw or raw[0].get("kind") != "case":
            errors.append("missing case registration")
            if fail_on_corruption:
                raise CorruptCase(errors[0])
            return RecoveredCase(case_id=case_id, action_ref="unknown", principal_id="unknown", current_state="UNKNOWN", sequence=0, last_receipt_digest=None, artifact_index=(), linked_remediation_cases=(), condition=CaseCondition.QUARANTINED, errors=tuple(errors))

        try:
            case = RegisteredCase(**raw[0]["payload"])
        except Exception as exc:
            errors.append(f"invalid case registration: {exc}")
            if fail_on_corruption:
                raise CorruptCase(errors[0]) from exc
            return RecoveredCase(case_id=case_id, action_ref="unknown", principal_id="unknown", current_state="UNKNOWN", sequence=0, last_receipt_digest=None, artifact_index=(), linked_remediation_cases=(), condition=CaseCondition.QUARANTINED, errors=tuple(errors))

        state = case.initial_state
        sequence = 0
        previous_digest: str | None = None
        artifacts: list[tuple[str, str]] = []
        remediation: list[str] = []
        seen_idempotency: set[str] = set()
        for record in raw[1:]:
            if record.get("kind") == "remediation_link":
                child = record.get("child_case_id")
                if not child or child in remediation:
                    errors.append("invalid or duplicate remediation link")
                else:
                    remediation.append(child)
                continue
            if record.get("kind") != "transition":
                errors.append("partial or unknown log record")
                continue
            try:
                transition = StoredTransition(**record["payload"])
            except Exception as exc:
                errors.append(f"invalid transition: {exc}")
                continue
            if transition.case_id != case.case_id or transition.action_ref != case.action_ref:
                errors.append("cross-case artifact injection")
            if transition.principal_id != case.principal_id:
                errors.append("principal mismatch")
            if transition.sequence != sequence + 1:
                errors.append("missing, reordered or duplicated sequence")
            if transition.previous_receipt_digest != previous_digest:
                errors.append("previous receipt digest mismatch")
            if transition.previous_state != state:
                errors.append("state chain mismatch")
            if transition.idempotency_key in seen_idempotency:
                errors.append("duplicate idempotency key")
            seen_idempotency.add(transition.idempotency_key)
            sequence = transition.sequence
            previous_digest = transition.receipt_digest
            state = transition.next_state
            artifacts.append((transition.artifact_type, transition.artifact_digest))

        if errors:
            condition = CaseCondition.QUARANTINED
        elif state in TERMINAL_STATES:
            condition = CaseCondition.TERMINAL
        elif state == "EXECUTING":
            condition = CaseCondition.INCOMPLETE_EXECUTION
        elif state in OUTCOME_PENDING_STATES:
            condition = CaseCondition.UNRESOLVED_OUTCOME
        else:
            condition = CaseCondition.RECOVERED_REVALIDATION_REQUIRED

        recovered = RecoveredCase(
            case_id=case.case_id, action_ref=case.action_ref, principal_id=case.principal_id,
            current_state=state, sequence=sequence, last_receipt_digest=previous_digest,
            artifact_index=tuple(artifacts), linked_remediation_cases=tuple(remediation),
            condition=condition, errors=tuple(errors), automatic_continuation_allowed=False,
            revalidation_required=condition not in {CaseCondition.TERMINAL, CaseCondition.QUARANTINED},
        )
        if errors and fail_on_corruption:
            raise CorruptCase("; ".join(errors))
        return recovered

    def verify_chain(self, case_id: str) -> VerificationResult:
        recovered = self.recover(case_id)
        chain_digest = canonical_digest({
            "case_id": recovered.case_id, "action_ref": recovered.action_ref,
            "sequence": recovered.sequence, "last_receipt_digest": recovered.last_receipt_digest,
            "artifact_index": recovered.artifact_index, "errors": recovered.errors,
        })
        return VerificationResult(case_id=case_id, valid=not recovered.errors, condition=recovered.condition, receipt_count=recovered.sequence, chain_digest=chain_digest, errors=recovered.errors, grants_authority=False)

    def export_evidence_package(
        self, case_id: str, *, unresolved_effects: Iterable[str] = (), dissent: Iterable[str] = (),
    ) -> EvidencePackage:
        raw = self.log.read(case_id)
        if not raw:
            raise CorruptCase("case not found")
        case = RegisteredCase(**raw[0]["payload"])
        transitions = tuple(StoredTransition(**record["payload"]) for record in raw if record.get("kind") == "transition")
        recovered = self.recover(case_id, fail_on_corruption=True)
        verification = self.verify_chain(case_id)
        provisional = EvidencePackage.model_construct(
            schema_version="1.0", case=case, transitions=transitions,
            artifact_linkage=recovered.artifact_index,
            linked_remediation_cases=recovered.linked_remediation_cases,
            unresolved_effects=tuple(unresolved_effects), dissent=tuple(dissent),
            verification=verification,
            lifecycle_trace=(case.initial_state,) + tuple(item.next_state for item in transitions),
            package_digest="sha256:" + "0" * 64,
        )
        return EvidencePackage(**{
            **provisional.model_dump(),
            "package_digest": evidence_package_digest(provisional),
        })


class ActionCaseVerificationService:
    """Provider-neutral evidence API. It records and verifies; it never authorizes."""

    def __init__(self, store: DurableActionCaseStore) -> None:
        self.store = store

    def register_case(self, case: RegisteredCase, *, idempotency_key: str) -> RegisteredCase:
        return self.store.register_case(case, idempotency_key=idempotency_key)

    def append_lifecycle_artifact(self, transition: StoredTransition, *, expected_sequence: int, expected_previous_digest: str | None) -> StoredTransition:
        return self.store.append_transition(transition, expected_sequence=expected_sequence, expected_previous_digest=expected_previous_digest)

    def get_current_verified_state(self, case_id: str) -> RecoveredCase:
        return self.store.recover(case_id)

    def verify_full_chain(self, case_id: str) -> VerificationResult:
        return self.store.verify_chain(case_id)

    def export_evidence_package(self, case_id: str, *, unresolved_effects: Iterable[str] = (), dissent: Iterable[str] = ()) -> EvidencePackage:
        return self.store.export_evidence_package(case_id, unresolved_effects=unresolved_effects, dissent=dissent)

    def register_linked_remediation_case(self, parent_case_id: str, remediation: RegisteredCase, *, idempotency_key: str) -> RegisteredCase:
        return self.store.register_remediation_case(parent_case_id, remediation, idempotency_key=idempotency_key)
