from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

from .memory_provider import MemoryProvider, MemoryRecord, MemoryStatus


@dataclass(frozen=True)
class MemoryContextItem:
    record: MemoryRecord
    stale: bool
    authoritative: bool = False


@dataclass(frozen=True)
class MemorySession:
    branch: str
    snapshot_id: str
    agent_id: str
    session_id: str
    task_id: str


def task_branch(agent_id: str, session_id: str, task_id: str) -> str:
    parts = (agent_id, session_id, task_id)
    if any(not part or "/" in part or ".." in part for part in parts):
        raise ValueError("agent_id, session_id and task_id must be non-empty safe path segments")
    return f"agent/{agent_id}/session/{session_id}/task/{task_id}"


class GovernedMemoryLifecycle:
    def __init__(self, provider: MemoryProvider, *, stale_after_seconds: int = 86_400) -> None:
        if stale_after_seconds < 0:
            raise ValueError("stale_after_seconds must be non-negative")
        self._provider = provider
        self._stale_after_seconds = stale_after_seconds

    async def begin(self, *, agent_id: str, session_id: str, task_id: str) -> MemorySession:
        branch = task_branch(agent_id, session_id, task_id)
        await self._provider.create_branch(branch)
        snapshot_id = await self._provider.create_snapshot(branch)
        return MemorySession(
            branch=branch,
            snapshot_id=snapshot_id,
            agent_id=agent_id,
            session_id=session_id,
            task_id=task_id,
        )

    async def bootstrap(self, session: MemorySession, query: str, *, limit: int = 20) -> tuple[MemoryContextItem, ...]:
        if not query.strip():
            return ()
        records: Sequence[MemoryRecord] = await self._provider.search_memory(
            query,
            branch=session.branch,
            limit=limit,
        )
        now = datetime.now(timezone.utc)
        items: list[MemoryContextItem] = []
        for record in records:
            age = max(0.0, (now - record.created_at).total_seconds())
            items.append(
                MemoryContextItem(
                    record=record,
                    stale=age > self._stale_after_seconds,
                    authoritative=False,
                )
            )
        return tuple(items)

    async def checkpoint(self, session: MemorySession) -> MemorySession:
        snapshot_id = await self._provider.create_snapshot(session.branch)
        return MemorySession(
            branch=session.branch,
            snapshot_id=snapshot_id,
            agent_id=session.agent_id,
            session_id=session.session_id,
            task_id=session.task_id,
        )

    async def cancel(self, session: MemorySession) -> str:
        # Cancellation restores the initial task snapshot. It never merges memory.
        return await self._provider.rollback_branch(session.branch, session.snapshot_id)

    async def complete(self, session: MemorySession) -> str:
        # Completion only freezes the branch. SOL promotion is a separate governed operation.
        return await self._provider.create_snapshot(session.branch)


def consequentially_usable(item: MemoryContextItem) -> bool:
    return (
        not item.stale
        and item.record.status is MemoryStatus.VALIDATED
        and item.authoritative is False
    )
