from __future__ import annotations

from pathlib import Path

import pytest

from valo_reht.consistency import ConsistencyScope, DeploymentTopology
from valo_reht.durable_permit_store import SQLitePermitStore
from valo_reht.effect_boundary import EffectBoundary
from valo_reht.execution_journal import SQLiteExecutionJournal
from valo_reht.runtime_interlocks import (
    ResourceBudget,
    ResourceBudgetLedger,
    ResourceReservation,
    RuntimeControlPlane,
    canonical_digest,
)


class _UnusedEvidenceSink:
    def close(self, receipt):  # pragma: no cover - construction-only test double
        raise AssertionError("construction tests must not close evidence")


class _DistributedPermitStore:
    production_safe = True
    consistency_scope = ConsistencyScope.DISTRIBUTED_CONSENSUS

    def consume_once(self, permit_ref: str) -> bool:
        raise AssertionError("construction-only test double")

    def is_consumed(self, permit_ref: str) -> bool:
        raise AssertionError("construction-only test double")


class _DistributedJournal:
    production_safe = True
    consistency_scope = ConsistencyScope.DISTRIBUTED_CONSENSUS

    def open_intent(self, **kwargs) -> bool:
        raise AssertionError("construction-only test double")

    def mark_effect_invoking(self, permit_ref: str) -> None:
        raise AssertionError("construction-only test double")

    def mark_receipt_ready(self, permit_ref: str, receipt) -> None:
        raise AssertionError("construction-only test double")

    def mark_evidence_closing(self, permit_ref: str) -> None:
        raise AssertionError("construction-only test double")

    def mark_closed(self, permit_ref: str, closure) -> None:
        raise AssertionError("construction-only test double")

    def get(self, permit_ref: str):
        raise AssertionError("construction-only test double")


class _DistributedRuntimeControl:
    consistency_scope = ConsistencyScope.DISTRIBUTED_CONSENSUS

    def check(self, action, execution_context):
        return None


class _DistributedResourceLedger:
    consistency_scope = ConsistencyScope.DISTRIBUTED_CONSENSUS

    def consume_once(self, reservation_id: str, *, action_digest: str, permit_ref: str) -> bool:
        raise AssertionError("construction-only test double")


class _UndeclaredProductionStore:
    production_safe = True


def _sqlite_pair(tmp_path: Path):
    return (
        SQLitePermitStore(tmp_path / "permits.sqlite3"),
        SQLiteExecutionJournal(tmp_path / "journal.sqlite3"),
    )


def test_sqlite_explicitly_declares_same_host_scope(tmp_path: Path) -> None:
    permit_store, journal = _sqlite_pair(tmp_path)
    assert permit_store.consistency_scope is ConsistencyScope.SAME_HOST_SHARED
    assert journal.consistency_scope is ConsistencyScope.SAME_HOST_SHARED


def test_single_host_production_still_accepts_sqlite(tmp_path: Path) -> None:
    permit_store, journal = _sqlite_pair(tmp_path)
    boundary = EffectBoundary(
        permit_store,
        evidence_sink=_UnusedEvidenceSink(),
        execution_journal=journal,
    )
    assert boundary.deployment_topology is DeploymentTopology.SINGLE_HOST


def test_multi_host_rejects_sqlite_permit_store_before_execution(tmp_path: Path) -> None:
    permit_store, journal = _sqlite_pair(tmp_path)
    with pytest.raises(ValueError, match="distributed-consensus permit store"):
        EffectBoundary(
            permit_store,
            evidence_sink=_UnusedEvidenceSink(),
            execution_journal=journal,
            deployment_topology=DeploymentTopology.MULTI_HOST,
        )


def test_multi_host_rejects_same_host_journal_even_with_distributed_permit(tmp_path: Path) -> None:
    journal = SQLiteExecutionJournal(tmp_path / "journal.sqlite3")
    with pytest.raises(ValueError, match="distributed-consensus execution journal"):
        EffectBoundary(
            _DistributedPermitStore(),
            evidence_sink=_UnusedEvidenceSink(),
            execution_journal=journal,
            deployment_topology="MULTI_HOST",
        )


def test_multi_host_rejects_undeclared_consistency_scope() -> None:
    with pytest.raises(ValueError, match="observed UNDECLARED"):
        EffectBoundary(
            _UndeclaredProductionStore(),  # type: ignore[arg-type]
            evidence_sink=_UnusedEvidenceSink(),
            execution_journal=_DistributedJournal(),
            deployment_topology="MULTI_HOST",
        )


def test_multi_host_rejects_default_process_local_runtime_control() -> None:
    with pytest.raises(ValueError, match="distributed-consensus runtime control"):
        EffectBoundary(
            _DistributedPermitStore(),
            evidence_sink=_UnusedEvidenceSink(),
            execution_journal=_DistributedJournal(),
            deployment_topology="MULTI_HOST",
        )


def test_multi_host_rejects_default_process_local_resource_ledger() -> None:
    with pytest.raises(ValueError, match="distributed-consensus resource ledger"):
        EffectBoundary(
            _DistributedPermitStore(),
            evidence_sink=_UnusedEvidenceSink(),
            execution_journal=_DistributedJournal(),
            runtime_control=_DistributedRuntimeControl(),  # type: ignore[arg-type]
            deployment_topology="MULTI_HOST",
        )


def test_process_local_halt_is_not_visible_to_peer_host() -> None:
    host_a = RuntimeControlPlane()
    host_b = RuntimeControlPlane()
    host_a.halt_global()
    assert host_a.check({}, {}) == "HALT_GLOBAL"
    assert host_b.check({}, {}) is None


def test_process_local_resource_ledgers_can_oversubscribe_global_budget() -> None:
    host_a = ResourceBudgetLedger()
    host_b = ResourceBudgetLedger()
    for ledger in (host_a, host_b):
        ledger.register_budget(ResourceBudget("global", {"units": 100.0}))
        ledger.reserve(
            ResourceReservation(
                reservation_id="reservation:full",
                budget_id="global",
                action_digest=canonical_digest({"action": "same-global-budget"}),
                amounts={"units": 100.0},
            )
        )
    # Each host independently accepts the full global ceiling: conceptual total=200.
    assert host_a.is_consumed("reservation:full") is False
    assert host_b.is_consumed("reservation:full") is False


def test_multi_host_accepts_only_complete_distributed_consistency_contract() -> None:
    boundary = EffectBoundary(
        _DistributedPermitStore(),
        evidence_sink=_UnusedEvidenceSink(),
        execution_journal=_DistributedJournal(),
        runtime_control=_DistributedRuntimeControl(),  # type: ignore[arg-type]
        resource_ledger=_DistributedResourceLedger(),  # type: ignore[arg-type]
        deployment_topology=DeploymentTopology.MULTI_HOST,
    )
    assert boundary.deployment_topology is DeploymentTopology.MULTI_HOST


def test_unknown_topology_fails_closed() -> None:
    with pytest.raises(ValueError, match="unknown deployment topology"):
        EffectBoundary(
            _DistributedPermitStore(),
            evidence_sink=_UnusedEvidenceSink(),
            execution_journal=_DistributedJournal(),
            runtime_control=_DistributedRuntimeControl(),  # type: ignore[arg-type]
            resource_ledger=_DistributedResourceLedger(),  # type: ignore[arg-type]
            deployment_topology="MAGIC_CLUSTER",
        )
