from datetime import datetime, timedelta, timezone

import pytest

from src.valo_platform.memory_provider import MemoryRecord, MemoryStatus, canonical_digest
from src.valo_platform.sol_memory_promotion import (
    HumanApprovalAttestation,
    SolPromotionRequest,
    execute_promotion,
    verify_promotion_replay,
)

NOW = datetime(2026, 7, 26, 21, 30, tzinfo=timezone.utc)
CONTENT = {"fact": "validated", "source": "receipt:1"}
DIGEST = canonical_digest(CONTENT)
EVIDENCE = canonical_digest({"memory_ids": ["mem-1"], "snapshot_id": "snap-1"})


def record(status: MemoryStatus = MemoryStatus.VALIDATED) -> MemoryRecord:
    return MemoryRecord(
        memory_id="mem-1",
        provider="memoria",
        provider_ref="provider-1",
        branch="agent/a/session/s/task/t",
        snapshot_id="snap-1",
        memory_type="research_finding",
        content_digest=DIGEST,
        source_refs=("source:1",),
        principal_id="principal-1",
        agent_id="agent-1",
        session_id="session-1",
        created_at=NOW,
        confidence=0.95,
        status=status,
        retention_class="canonical-candidate",
    )


def request() -> SolPromotionRequest:
    return SolPromotionRequest(
        request_id="request-1",
        principal_id="principal-1",
        source_memory_id="mem-1",
        source_snapshot_id="snap-1",
        source_evidence_digest=EVIDENCE,
        target_namespace="research/validated",
        proposed_content_digest=DIGEST,
        requested_at=NOW,
    )


def approval(**changes) -> HumanApprovalAttestation:
    data = dict(
        attestation_id="approval-1",
        principal_id="principal-1",
        approver_id="human-1",
        source_evidence_digest=EVIDENCE,
        target_namespace="research/validated",
        approved_at=NOW,
        expires_at=NOW + timedelta(minutes=10),
    )
    data.update(changes)
    return HumanApprovalAttestation(**data)


def test_valid_promotion_emits_separate_replayable_receipt() -> None:
    receipt = execute_promotion(
        request=request(),
        approval=approval(),
        record=record(),
        content=CONTENT,
        stale=False,
        receipt_id="promotion-1",
        now=NOW + timedelta(minutes=1),
    )
    assert verify_promotion_replay(request=request(), approval=approval(), receipt=receipt)
    assert receipt.grants_authority is False
    assert receipt.is_governance_clearance is False
    assert receipt.is_execution_receipt is False


@pytest.mark.parametrize("status", [MemoryStatus.WORKING, MemoryStatus.CANDIDATE, MemoryStatus.QUARANTINED])
def test_non_validated_memory_is_rejected(status: MemoryStatus) -> None:
    with pytest.raises(ValueError, match="only validated"):
        execute_promotion(
            request=request(), approval=approval(), record=record(status), content=CONTENT,
            stale=False, receipt_id="promotion-1", now=NOW
        )


def test_stale_memory_is_rejected() -> None:
    with pytest.raises(ValueError, match="stale"):
        execute_promotion(
            request=request(), approval=approval(), record=record(), content=CONTENT,
            stale=True, receipt_id="promotion-1", now=NOW
        )


def test_scope_mismatched_approval_is_rejected() -> None:
    with pytest.raises(ValueError, match="namespace"):
        execute_promotion(
            request=request(), approval=approval(target_namespace="other"), record=record(),
            content=CONTENT, stale=False, receipt_id="promotion-1", now=NOW
        )


def test_expired_approval_is_rejected() -> None:
    with pytest.raises(ValueError, match="expired"):
        execute_promotion(
            request=request(), approval=approval(), record=record(), content=CONTENT,
            stale=False, receipt_id="promotion-1", now=NOW + timedelta(minutes=11)
        )


def test_mutated_content_is_rejected() -> None:
    with pytest.raises(ValueError, match="digest mismatch"):
        execute_promotion(
            request=request(), approval=approval(), record=record(), content={"fact": "changed"},
            stale=False, receipt_id="promotion-1", now=NOW
        )
