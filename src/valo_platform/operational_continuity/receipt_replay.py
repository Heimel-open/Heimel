"""Receipt construction and deterministic replay for Operational Continuity."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field

from src.valo_platform.action_envelope.models import ActionDecision
from src.valo_platform.decision_governance.continuity import (
    ContinuityBasisSnapshot,
    ContinuityContractError,
    ContinuityDecision,
    ContinuityImpactAssessment,
    ContinuityTrigger,
    canonical_digest,
    require_same_binding,
)


_GENESIS_HASH = "0" * 64


class ContinuityReceiptRecord(BaseModel):
    """Append-only replay record for one complete continuity decision chain."""

    model_config = ConfigDict(frozen=True, extra="forbid", use_enum_values=False)

    record_id: str
    sequence: int = Field(ge=0)
    tenant_id: str
    action_case_id: str
    action_case_hash: str
    clearance_ref: str
    basis: ContinuityBasisSnapshot
    triggers: tuple[ContinuityTrigger, ...]
    assessment: ContinuityImpactAssessment
    decision: ContinuityDecision
    enforcement_outcome: ActionDecision
    execution_receipt_ref: str | None = None
    execution_receipt_snapshot: dict[str, Any] | None = None
    recorded_at: datetime
    previous_chain_hash: str = _GENESIS_HASH
    record_digest: str
    chain_hash: str


class ContinuityReplayResult(BaseModel):
    """Deterministic verification result; carries no execution authority."""

    model_config = ConfigDict(frozen=True, extra="forbid", use_enum_values=False)

    valid: bool
    errors: tuple[str, ...]
    action_case_id: str
    clearance_ref: str
    decision: ActionDecision
    execution_recorded: bool
    final_chain_hash: str


def _without_digest(model: BaseModel, digest_field: str) -> dict[str, Any]:
    return model.model_dump(mode="json", exclude={digest_field})


def _receipt_metadata(snapshot: Mapping[str, Any]) -> Mapping[str, Any]:
    metadata = snapshot.get("metadata")
    return metadata if isinstance(metadata, Mapping) else {}


def _validate_refs(
    *,
    basis: ContinuityBasisSnapshot,
    triggers: Sequence[ContinuityTrigger],
    assessment: ContinuityImpactAssessment,
    decision: ContinuityDecision,
) -> None:
    require_same_binding(basis, triggers, assessment)
    expected = (
        basis.tenant_id,
        basis.action_case_id,
        basis.action_case_hash,
        basis.clearance_ref,
    )
    actual = (
        decision.tenant_id,
        decision.action_case_id,
        decision.action_case_hash,
        decision.clearance_ref,
    )
    if actual != expected:
        raise ContinuityContractError("continuity decision binding mismatch")
    if decision.basis_snapshot_ref != basis.snapshot_id:
        raise ContinuityContractError("continuity basis reference mismatch")
    if decision.basis_snapshot_digest != basis.snapshot_digest:
        raise ContinuityContractError("continuity basis digest mismatch")
    if set(decision.trigger_refs) != {item.trigger_id for item in triggers}:
        raise ContinuityContractError("continuity decision trigger set mismatch")
    if set(decision.impact_assessment_refs) != {assessment.assessment_id}:
        raise ContinuityContractError("continuity assessment reference mismatch")


def _validate_execution_snapshot(
    *,
    snapshot: Mapping[str, Any],
    decision: ContinuityDecision,
) -> tuple[str, ActionDecision]:
    metadata = _receipt_metadata(snapshot)
    expected_metadata = {
        "action_case_ref": decision.action_case_id,
        "action_case_hash": decision.action_case_hash,
        "clearance_ref": decision.clearance_ref,
        "continuity_basis_snapshot_ref": decision.basis_snapshot_ref,
        "continuity_decision_ref": decision.continuity_decision_id,
        "continuity_decision_digest": decision.decision_digest,
    }
    for key, expected in expected_metadata.items():
        if metadata.get(key) != expected:
            raise ContinuityContractError(
                f"execution receipt continuity metadata mismatch: {key}"
            )
    if set(metadata.get("continuity_trigger_refs") or ()) != set(
        decision.trigger_refs
    ):
        raise ContinuityContractError(
            "execution receipt continuity trigger mismatch"
        )
    if set(metadata.get("continuity_assessment_refs") or ()) != set(
        decision.impact_assessment_refs
    ):
        raise ContinuityContractError(
            "execution receipt continuity assessment mismatch"
        )
    raw_outcome = snapshot.get("decision")
    try:
        outcome = (
            raw_outcome
            if isinstance(raw_outcome, ActionDecision)
            else ActionDecision(str(raw_outcome))
        )
    except ValueError as exc:
        raise ContinuityContractError(
            "execution receipt contains unknown outcome"
        ) from exc
    receipt_ref = str(snapshot.get("receipt_id") or "")
    if not receipt_ref:
        raise ContinuityContractError("execution receipt reference missing")
    if outcome != decision.racs_outcome:
        raise ContinuityContractError(
            "execution receipt outcome does not match continuity decision"
        )
    return receipt_ref, outcome


def _record_payload(
    *,
    record_id: str,
    sequence: int,
    tenant_id: str,
    action_case_id: str,
    action_case_hash: str,
    clearance_ref: str,
    basis: ContinuityBasisSnapshot,
    triggers: Sequence[ContinuityTrigger],
    assessment: ContinuityImpactAssessment,
    decision: ContinuityDecision,
    enforcement_outcome: ActionDecision,
    execution_receipt_ref: str | None,
    execution_receipt_snapshot: Mapping[str, Any] | None,
    recorded_at: datetime,
    previous_chain_hash: str,
) -> dict[str, Any]:
    return {
        "record_id": record_id,
        "sequence": sequence,
        "tenant_id": tenant_id,
        "action_case_id": action_case_id,
        "action_case_hash": action_case_hash,
        "clearance_ref": clearance_ref,
        "basis": basis.model_dump(mode="json"),
        "triggers": [item.model_dump(mode="json") for item in triggers],
        "assessment": assessment.model_dump(mode="json"),
        "decision": decision.model_dump(mode="json"),
        "enforcement_outcome": enforcement_outcome.value,
        "execution_receipt_ref": execution_receipt_ref,
        "execution_receipt_snapshot": (
            dict(execution_receipt_snapshot)
            if execution_receipt_snapshot is not None
            else None
        ),
        "recorded_at": recorded_at,
        "previous_chain_hash": previous_chain_hash,
    }


def build_continuity_receipt_record(
    *,
    sequence: int,
    basis: ContinuityBasisSnapshot,
    triggers: Sequence[ContinuityTrigger],
    assessment: ContinuityImpactAssessment,
    decision: ContinuityDecision,
    recorded_at: datetime,
    previous_chain_hash: str = _GENESIS_HASH,
    execution_receipt_snapshot: Mapping[str, Any] | None = None,
) -> ContinuityReceiptRecord:
    """Build one immutable record after validating the complete reference chain."""

    if not triggers:
        raise ContinuityContractError(
            "continuity receipt requires at least one trigger"
        )
    _validate_refs(
        basis=basis,
        triggers=triggers,
        assessment=assessment,
        decision=decision,
    )

    execution_receipt_ref: str | None = None
    enforcement_outcome = decision.racs_outcome
    snapshot_copy: dict[str, Any] | None = None
    if execution_receipt_snapshot is not None:
        execution_receipt_ref, enforcement_outcome = _validate_execution_snapshot(
            snapshot=execution_receipt_snapshot,
            decision=decision,
        )
        snapshot_copy = dict(execution_receipt_snapshot)
    elif decision.racs_outcome == ActionDecision.ALLOW:
        raise ContinuityContractError(
            "ALLOW continuity record requires execution receipt evidence"
        )

    record_id = (
        f"continuity-record:{basis.action_case_id}:"
        f"{sequence}:{decision.decision_digest.split(':', 1)[-1][:16]}"
    )
    payload = _record_payload(
        record_id=record_id,
        sequence=sequence,
        tenant_id=basis.tenant_id,
        action_case_id=basis.action_case_id,
        action_case_hash=basis.action_case_hash,
        clearance_ref=basis.clearance_ref,
        basis=basis,
        triggers=triggers,
        assessment=assessment,
        decision=decision,
        enforcement_outcome=enforcement_outcome,
        execution_receipt_ref=execution_receipt_ref,
        execution_receipt_snapshot=snapshot_copy,
        recorded_at=recorded_at,
        previous_chain_hash=previous_chain_hash,
    )
    record_digest = canonical_digest(payload)
    chain_hash = canonical_digest(
        {
            "previous_chain_hash": previous_chain_hash,
            "record_digest": record_digest,
        }
    )
    return ContinuityReceiptRecord(
        **payload,
        record_digest=record_digest,
        chain_hash=chain_hash,
    )


def replay_continuity_receipt(
    record: ContinuityReceiptRecord,
) -> ContinuityReplayResult:
    """Verify all nested digests, bindings, receipt metadata and chain hashes."""

    errors: list[str] = []
    try:
        _validate_refs(
            basis=record.basis,
            triggers=record.triggers,
            assessment=record.assessment,
            decision=record.decision,
        )
    except ContinuityContractError as exc:
        errors.append(str(exc))

    if canonical_digest(
        _without_digest(record.basis, "snapshot_digest")
    ) != record.basis.snapshot_digest:
        errors.append("basis digest mismatch")
    for trigger in record.triggers:
        if canonical_digest(
            _without_digest(trigger, "trigger_digest")
        ) != trigger.trigger_digest:
            errors.append(f"trigger digest mismatch: {trigger.trigger_id}")
    if canonical_digest(
        _without_digest(record.assessment, "assessment_digest")
    ) != record.assessment.assessment_digest:
        errors.append("assessment digest mismatch")
    if canonical_digest(
        _without_digest(record.decision, "decision_digest")
    ) != record.decision.decision_digest:
        errors.append("decision digest mismatch")

    if record.execution_receipt_snapshot is not None:
        try:
            receipt_ref, outcome = _validate_execution_snapshot(
                snapshot=record.execution_receipt_snapshot,
                decision=record.decision,
            )
            if receipt_ref != record.execution_receipt_ref:
                errors.append("execution receipt reference mismatch")
            if outcome != record.enforcement_outcome:
                errors.append("enforcement outcome mismatch")
        except ContinuityContractError as exc:
            errors.append(str(exc))
    elif record.decision.racs_outcome == ActionDecision.ALLOW:
        errors.append("ALLOW record missing execution receipt")

    payload = _record_payload(
        record_id=record.record_id,
        sequence=record.sequence,
        tenant_id=record.tenant_id,
        action_case_id=record.action_case_id,
        action_case_hash=record.action_case_hash,
        clearance_ref=record.clearance_ref,
        basis=record.basis,
        triggers=record.triggers,
        assessment=record.assessment,
        decision=record.decision,
        enforcement_outcome=record.enforcement_outcome,
        execution_receipt_ref=record.execution_receipt_ref,
        execution_receipt_snapshot=record.execution_receipt_snapshot,
        recorded_at=record.recorded_at,
        previous_chain_hash=record.previous_chain_hash,
    )
    expected_record_digest = canonical_digest(payload)
    if expected_record_digest != record.record_digest:
        errors.append("record digest mismatch")
    expected_chain_hash = canonical_digest(
        {
            "previous_chain_hash": record.previous_chain_hash,
            "record_digest": record.record_digest,
        }
    )
    if expected_chain_hash != record.chain_hash:
        errors.append("chain hash mismatch")

    return ContinuityReplayResult(
        valid=not errors,
        errors=tuple(errors),
        action_case_id=record.action_case_id,
        clearance_ref=record.clearance_ref,
        decision=record.decision.racs_outcome,
        execution_recorded=record.execution_receipt_ref is not None,
        final_chain_hash=record.chain_hash,
    )


def verify_continuity_receipt_chain(
    records: Sequence[ContinuityReceiptRecord],
) -> ContinuityReplayResult:
    """Verify deterministic order and chaining for a complete continuity history."""

    if not records:
        raise ContinuityContractError("continuity receipt chain is empty")
    errors: list[str] = []
    expected_previous = _GENESIS_HASH
    expected_sequence = 0
    for record in records:
        if record.sequence != expected_sequence:
            errors.append(
                f"sequence mismatch: expected {expected_sequence}, got {record.sequence}"
            )
        if record.previous_chain_hash != expected_previous:
            errors.append(f"previous chain mismatch at sequence {record.sequence}")
        replay = replay_continuity_receipt(record)
        errors.extend(
            f"sequence {record.sequence}: {error}" for error in replay.errors
        )
        expected_previous = record.chain_hash
        expected_sequence += 1

    final = records[-1]
    return ContinuityReplayResult(
        valid=not errors,
        errors=tuple(errors),
        action_case_id=final.action_case_id,
        clearance_ref=final.clearance_ref,
        decision=final.decision.racs_outcome,
        execution_recorded=final.execution_receipt_ref is not None,
        final_chain_hash=final.chain_hash,
    )


__all__ = [
    "ContinuityReceiptRecord",
    "ContinuityReplayResult",
    "build_continuity_receipt_record",
    "replay_continuity_receipt",
    "verify_continuity_receipt_chain",
]
