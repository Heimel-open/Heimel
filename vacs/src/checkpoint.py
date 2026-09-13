"""
VACS checkpoint interface.

Recovered from VAIG Fidelity as the rollback substrate. This implementation is
in-memory and deterministic enough for tests; production adapters can replace the
store while preserving the same interface.
"""

import time
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class CheckpointRecord:
    checkpoint_id: str
    label: str
    container_id: str
    timestamp: float
    state_hash: Optional[str] = None


class CheckpointStore:
    def __init__(self):
        self._checkpoints: Dict[str, CheckpointRecord] = {}

    def save(self, record: CheckpointRecord) -> None:
        self._checkpoints[record.checkpoint_id] = record

    def load(self, checkpoint_id: str) -> Optional[CheckpointRecord]:
        return self._checkpoints.get(checkpoint_id)

    def list_checkpoints(self, container_id: Optional[str] = None) -> List[str]:
        ids = [
            checkpoint_id
            for checkpoint_id, record in self._checkpoints.items()
            if container_id is None or record.container_id == container_id
        ]
        return sorted(ids)


class CheckpointManager:
    def __init__(self, container_id: str, store: Optional[CheckpointStore] = None):
        if not container_id:
            raise ValueError("container_id is required")
        self.container_id = container_id
        self.store = store or CheckpointStore()
        self._active_checkpoint: Optional[str] = None
        self._checkpoint_count = 0
        self._rollback_count = 0

    def checkpoint(self, label: str, state_hash: Optional[str] = None) -> str:
        if not label:
            raise ValueError("label is required")
        checkpoint_id = f"cp_{label}_{uuid.uuid4().hex[:8]}"
        record = CheckpointRecord(
            checkpoint_id=checkpoint_id,
            label=label,
            container_id=self.container_id,
            timestamp=time.time(),
            state_hash=state_hash,
        )
        self.store.save(record)
        self._active_checkpoint = checkpoint_id
        self._checkpoint_count += 1
        return checkpoint_id

    def rollback(self, checkpoint_id: str) -> bool:
        if self.store.load(checkpoint_id) is None:
            return False
        self._active_checkpoint = checkpoint_id
        self._rollback_count += 1
        return True

    def get_active_checkpoint(self) -> Optional[str]:
        return self._active_checkpoint

    def get_stats(self) -> Dict[str, object]:
        return {
            "checkpoint_count": self._checkpoint_count,
            "rollback_count": self._rollback_count,
            "active_checkpoint": self._active_checkpoint,
            "container_id": self.container_id,
        }