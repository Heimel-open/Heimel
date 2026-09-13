from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.valo_platform.memory_provider import MemoryRecord, MemoryStatus, canonical_digest


def valid_record(**overrides):
    payload = {
        "memory_id": "mem-1",
        "provider": "memoria",
        "provider_ref": "provider/mem-1",
        "branch": "agent/a/session/s/task/t",
        "snapshot_id": "snap-1",
        "memory_type": "working",
        "content_digest": canonical_digest({"fact": "x"}),
        "source_refs": ("source-1",),
        "principal_id": "principal-1",
        "agent_id": "agent-1",
        "session_id": "session-1",
        "created_at": datetime.now(timezone.utc),
        "confidence": 0.8,
        "status": MemoryStatus.WORKING,
        "retention_class": "session",
    }
    payload.update(overrides)
    return payload


def test_canonical_digest_is_order_independent():
    assert canonical_digest({"b": 2, "a": 1}) == canonical_digest({"a": 1, "b": 2})


def test_unknown_fields_are_rejected():
    with pytest.raises(ValidationError):
        MemoryRecord.model_validate(valid_record(memoria_internal="leak"))


@pytest.mark.parametrize(
    "memory_type",
    [
        "legal_mandate",
        "delegation",
        "human_approval",
        "governance_clearance",
        "execution_receipt",
        "outcome_evidence",
    ],
)
def test_authoritative_objects_cannot_be_mutable_memory(memory_type):
    with pytest.raises(ValidationError):
        MemoryRecord.model_validate(valid_record(memory_type=memory_type))


def test_valid_working_memory_is_accepted():
    record = MemoryRecord.model_validate(valid_record())
    assert record.status is MemoryStatus.WORKING
    assert record.provider == "memoria"
