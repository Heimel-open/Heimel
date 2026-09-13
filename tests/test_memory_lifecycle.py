from datetime import datetime, timedelta, timezone

import pytest

from src.valo_platform.memory_lifecycle import (
    GovernedMemoryLifecycle,
    consequentially_usable,
    task_branch,
)
from src.valo_platform.memory_provider import MemoryRecord, MemoryStatus


class FakeProvider:
    def __init__(self):
        self.calls = []
        self.records = []

    async def create_branch(self, branch, from_snapshot=None):
        self.calls.append(("create_branch", branch, from_snapshot))
        return branch

    async def create_snapshot(self, branch):
        self.calls.append(("create_snapshot", branch))
        return f"snap:{len(self.calls)}"

    async def search_memory(self, query, *, branch, limit=20):
        self.calls.append(("search_memory", query, branch, limit))
        return self.records

    async def rollback_branch(self, branch, snapshot_id):
        self.calls.append(("rollback_branch", branch, snapshot_id))
        return snapshot_id


def record(*, status=MemoryStatus.VALIDATED, created_at=None):
    return MemoryRecord(
        memory_id="m1",
        provider="memoria",
        provider_ref="p1",
        branch="agent/a/session/s/task/t",
        snapshot_id="snap:1",
        memory_type="working",
        content_digest="sha256:" + "0" * 64,
        source_refs=("source:1",),
        principal_id="principal",
        agent_id="a",
        session_id="s",
        created_at=created_at or datetime.now(timezone.utc),
        confidence=0.9,
        status=status,
        retention_class="session",
    )


def test_task_branch_is_scoped_and_rejects_path_escape():
    assert task_branch("a", "s", "t") == "agent/a/session/s/task/t"
    with pytest.raises(ValueError):
        task_branch("../a", "s", "t")


@pytest.mark.asyncio
async def test_begin_creates_isolated_branch_and_initial_snapshot():
    provider = FakeProvider()
    lifecycle = GovernedMemoryLifecycle(provider)

    session = await lifecycle.begin(agent_id="a", session_id="s", task_id="t")

    assert session.branch == "agent/a/session/s/task/t"
    assert provider.calls[0][0] == "create_branch"
    assert provider.calls[1][0] == "create_snapshot"


@pytest.mark.asyncio
async def test_cancel_rolls_back_and_never_merges():
    provider = FakeProvider()
    lifecycle = GovernedMemoryLifecycle(provider)
    session = await lifecycle.begin(agent_id="a", session_id="s", task_id="t")

    await lifecycle.cancel(session)

    assert any(call[0] == "rollback_branch" for call in provider.calls)
    assert not any(call[0] == "merge_branch" for call in provider.calls)


@pytest.mark.asyncio
async def test_bootstrap_discloses_stale_memory():
    provider = FakeProvider()
    provider.records = [record(created_at=datetime.now(timezone.utc) - timedelta(days=2))]
    lifecycle = GovernedMemoryLifecycle(provider, stale_after_seconds=60)
    session = await lifecycle.begin(agent_id="a", session_id="s", task_id="t")

    items = await lifecycle.bootstrap(session, "query")

    assert items[0].stale is True
    assert items[0].authoritative is False
    assert consequentially_usable(items[0]) is False


def test_only_fresh_validated_non_authoritative_context_is_usable():
    from src.valo_platform.memory_lifecycle import MemoryContextItem

    assert consequentially_usable(MemoryContextItem(record=record(), stale=False)) is True
    assert consequentially_usable(
        MemoryContextItem(record=record(status=MemoryStatus.WORKING), stale=False)
    ) is False
