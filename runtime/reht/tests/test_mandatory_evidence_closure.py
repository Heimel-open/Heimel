from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import pytest

from valo_reht import (
    BoundaryEffect,
    DevelopmentEvidenceClosureSink,
    DevelopmentExecutionJournal,
    EffectBoundary,
    EvidenceClosureError,
    InMemoryPermitStore,
    SQLiteExecutionJournal,
    SQLitePermitStore,
    VeritasKernelExecutionEvidenceSink,
)
from valo_reht.contracts import DecisionResult
from valo_reht.runtime_interlocks import build_execution_receipt


def _digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(dict(payload), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _action() -> dict[str, Any]:
    return {
        "action_id": "action:closure",
        "capability": "DO_EFFECT",
        "target": "target:1",
    }


def _context(_: dict[str, Any]) -> dict[str, Any]:
    return {"kernel_sequence": 12, "state": "READY"}


class StaticReht:
    def __init__(self, decision: str = "ALLOW") -> None:
        self.decision = decision

    def authorize(
        self,
        execution_context: dict[str, Any],
        action_contract: dict[str, Any],
    ) -> DecisionResult:
        if self.decision != "ALLOW":
            return DecisionResult(decision=self.decision, reason="restricted")
        return DecisionResult(
            decision="ALLOW",
            clearance_ref="clearance:closure",
            permit_ref="permit:closure",
            execution_context_hash=_digest(execution_context),
        )


class FakeVeritas:
    def __init__(self, events: list[str], *, fail: bool = False) -> None:
        self.events = events
        self.fail = fail
        self.payloads: list[Mapping[str, Any]] = []

    def store_effect_boundary_execution_observation(
        self,
        payload: Mapping[str, Any],
    ) -> str:
        self.events.append("VERITAS")
        self.payloads.append(dict(payload))
        if self.fail:
            raise ValueError("tampered")
        return "a" * 64


class FakeKernel:
    def __init__(self, events: list[str], *, fail: bool = False) -> None:
        self.events = events
        self.fail = fail
        self.outcomes: list[Mapping[str, Any]] = []

    def append_verified_execution_outcome(
        self,
        outcome: Mapping[str, Any],
    ) -> str:
        self.events.append("KERNEL")
        self.outcomes.append(dict(outcome))
        if self.fail:
            raise RuntimeError("kernel append failed")
        return "kernel-event:" + "b" * 64


def _receipt():
    return build_execution_receipt(
        status="COMMITTED",
        action=_action(),
        execution_context_hash="c" * 64,
        reht_decision="ALLOW",
        clearance_ref="clearance:closure",
        permit_ref="permit:closure",
        effect_name="closure-effect",
        effect_result={"ok": True},
    )


def _durable_store(tmp_path: Path) -> SQLitePermitStore:
    return SQLitePermitStore(tmp_path / "permits.sqlite3")


def _durable_journal(tmp_path: Path) -> SQLiteExecutionJournal:
    return SQLiteExecutionJournal(tmp_path / "execution-journal.sqlite3")


def test_production_boundary_rejects_inmemory_permit_store() -> None:
    with pytest.raises(ValueError, match="production-safe"):
        EffectBoundary(
            InMemoryPermitStore(),
            evidence_sink=VeritasKernelExecutionEvidenceSink(
                veritas=FakeVeritas([]),
                kernel=FakeKernel([]),
            ),
            execution_journal=DevelopmentExecutionJournal(),
        )


def test_production_boundary_rejects_development_execution_journal(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="production-safe execution journal"):
        EffectBoundary(
            _durable_store(tmp_path),
            evidence_sink=VeritasKernelExecutionEvidenceSink(
                veritas=FakeVeritas([]),
                kernel=FakeKernel([]),
            ),
            execution_journal=DevelopmentExecutionJournal(),
        )


def test_production_boundary_rejects_development_evidence_sink(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cannot use development evidence sink"):
        EffectBoundary(
            _durable_store(tmp_path),
            evidence_sink=DevelopmentEvidenceClosureSink(),
            execution_journal=_durable_journal(tmp_path),
        )


def test_development_mode_is_explicit_and_never_claims_closure() -> None:
    boundary = EffectBoundary.for_development(InMemoryPermitStore())
    result = boundary.commit(
        reht=StaticReht(),
        context_factory=_context,
        action_contract=_action(),
        effect=BoundaryEffect.seal("closure-effect", lambda action: {"ok": True}),
    )
    assert result.effect_committed is True
    assert result.evidence_closure is not None
    assert result.evidence_closure.closed is False
    assert result.evidence_closure.veritas_ref is None
    assert result.evidence_closure.kernel_ref is None


def test_production_sink_closes_veritas_then_kernel_in_order() -> None:
    events: list[str] = []
    veritas = FakeVeritas(events)
    kernel = FakeKernel(events)
    sink = VeritasKernelExecutionEvidenceSink(veritas=veritas, kernel=kernel)

    closure = sink.close(_receipt())

    assert events == ["VERITAS", "KERNEL"]
    assert closure.closed is True
    assert closure.veritas_ref == "veritas-worm:sha256:" + "a" * 64
    assert closure.kernel_ref == "kernel-event:" + "b" * 64
    assert closure.authority_granted is False
    assert veritas.payloads[0]["schema"] == "valo.reht.effect-boundary-observation.v1"
    assert veritas.payloads[0]["authority_granted"] is False
    assert kernel.outcomes[0]["veritas_ref"] == closure.veritas_ref
    assert kernel.outcomes[0]["authority_granted"] is False


def test_veritas_failure_stops_before_kernel_and_never_closes() -> None:
    events: list[str] = []
    sink = VeritasKernelExecutionEvidenceSink(
        veritas=FakeVeritas(events, fail=True),
        kernel=FakeKernel(events),
    )

    with pytest.raises(EvidenceClosureError) as excinfo:
        sink.close(_receipt())

    assert excinfo.value.stage == "VERITAS"
    assert excinfo.value.veritas_ref is None
    assert events == ["VERITAS"]


def test_kernel_failure_after_worm_is_explicit_incomplete_closure() -> None:
    events: list[str] = []
    sink = VeritasKernelExecutionEvidenceSink(
        veritas=FakeVeritas(events),
        kernel=FakeKernel(events, fail=True),
    )

    with pytest.raises(EvidenceClosureError) as excinfo:
        sink.close(_receipt())

    assert excinfo.value.stage == "KERNEL"
    assert excinfo.value.veritas_ref == "veritas-worm:sha256:" + "a" * 64
    assert events == ["VERITAS", "KERNEL"]


def test_production_boundary_returns_only_after_closed_evidence(tmp_path: Path) -> None:
    events: list[str] = []
    sink = VeritasKernelExecutionEvidenceSink(
        veritas=FakeVeritas(events),
        kernel=FakeKernel(events),
    )
    boundary = EffectBoundary(
        _durable_store(tmp_path),
        evidence_sink=sink,
        execution_journal=_durable_journal(tmp_path),
    )
    effect_calls: list[dict[str, Any]] = []

    result = boundary.commit(
        reht=StaticReht(),
        context_factory=_context,
        action_contract=_action(),
        effect=BoundaryEffect.seal(
            "closure-effect",
            lambda action: effect_calls.append(action) or {"ok": True},
        ),
    )

    assert effect_calls == [_action()]
    assert events == ["VERITAS", "KERNEL"]
    assert result.effect_committed is True
    assert result.valid_completion is True
    assert result.evidence_closure is not None
    assert result.evidence_closure.closed is True


def test_restrictive_reht_outcome_is_also_evidence_closed_before_return(tmp_path: Path) -> None:
    events: list[str] = []
    sink = VeritasKernelExecutionEvidenceSink(
        veritas=FakeVeritas(events),
        kernel=FakeKernel(events),
    )
    boundary = EffectBoundary(
        _durable_store(tmp_path),
        evidence_sink=sink,
        execution_journal=_durable_journal(tmp_path),
    )
    effect_calls: list[dict[str, Any]] = []

    result = boundary.commit(
        reht=StaticReht("DENY"),
        context_factory=_context,
        action_contract=_action(),
        effect=BoundaryEffect.seal(
            "closure-effect",
            lambda action: effect_calls.append(action),
        ),
    )

    assert effect_calls == []
    assert result.effect_committed is False
    assert result.valid_completion is False
    assert result.evidence_closure is not None
    assert result.evidence_closure.closed is True
    assert events == ["VERITAS", "KERNEL"]
