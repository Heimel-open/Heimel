from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tests.two_core_harness import (
    CAPABILITY,
    PURPOSE,
    TARGET,
    _revoke_event,
    base_engine,
    build_context,
)
from valo_reht import (
    BoundaryEffect,
    EffectBoundary,
    RealReht,
    SQLiteExecutionJournal,
    SQLitePermitStore,
)
from valo_reht.evidence_closure import EvidenceClosure

NOW = datetime(2026, 8, 23, 18, 55, tzinfo=UTC)


class ClosedEvidenceSink:
    def close(self, receipt):
        return EvidenceClosure(
            receipt_id=receipt.receipt_id,
            veritas_ref="veritas-worm:sha256:" + "a" * 64,
            kernel_ref="kernel-event:" + "b" * 64,
            closed=True,
        )


def _action(*, step_up: bool = False) -> dict[str, Any]:
    action: dict[str, Any] = {
        "action_id": "action:production-boundary",
        "capability": CAPABILITY,
        "target": TARGET,
        "action_type": CAPABILITY,
        "purpose_id": PURPOSE,
    }
    if step_up:
        action["step_up"] = {
            "required": True,
            "reason": "higher assurance required",
        }
    return action


def _boundary(tmp_path: Path) -> tuple[EffectBoundary, SQLitePermitStore]:
    store = SQLitePermitStore(tmp_path / "permits.sqlite3")
    journal = SQLiteExecutionJournal(tmp_path / "execution-journal.sqlite3")
    return (
        EffectBoundary(
            store,
            evidence_sink=ClosedEvidenceSink(),
            execution_journal=journal,
        ),
        store,
    )


def test_real_reht_kernel_path_commits_exact_action_once(tmp_path: Path) -> None:
    engine = base_engine(now=NOW)
    boundary, store = _boundary(tmp_path)
    effects: list[dict[str, Any]] = []

    result = boundary.commit(
        reht=RealReht(),
        context_factory=lambda action: build_context(
            engine,
            action,
            now=NOW,
            nonce="nonce:production:allow",
        ),
        action_contract=_action(),
        effect=BoundaryEffect.seal(
            "integration-effect",
            lambda action: effects.append(action) or {"ok": True},
        ),
    )

    assert result.decision.decision == "ALLOW"
    assert result.effect_committed is True
    assert result.valid_completion is True
    assert result.receipt is not None
    assert result.receipt.status == "COMMITTED"
    assert result.evidence_closure is not None
    assert result.evidence_closure.closed is True
    assert effects == [_action()]
    assert result.decision.permit_ref is not None
    assert store.is_consumed(result.decision.permit_ref) is True


def test_revocation_is_seen_before_production_commit(tmp_path: Path) -> None:
    engine = base_engine(now=NOW)
    engine.append(_revoke_event(now=NOW))
    boundary, _ = _boundary(tmp_path)
    effects: list[dict[str, Any]] = []

    result = boundary.commit(
        reht=RealReht(),
        context_factory=lambda action: build_context(
            engine,
            action,
            now=NOW,
            nonce="nonce:production:revoked",
        ),
        action_contract=_action(),
        effect=BoundaryEffect.seal("integration-effect", lambda action: effects.append(action)),
    )

    assert result.decision.decision == "DENY"
    assert result.effect_committed is False
    assert result.receipt is not None
    assert result.receipt.status == "NOT_COMMITTED"
    assert result.evidence_closure is not None
    assert result.evidence_closure.closed is True
    assert effects == []


def test_step_up_never_crosses_production_effect_boundary(tmp_path: Path) -> None:
    engine = base_engine(now=NOW)
    boundary, _ = _boundary(tmp_path)
    effects: list[dict[str, Any]] = []

    result = boundary.commit(
        reht=RealReht(),
        context_factory=lambda action: build_context(
            engine,
            action,
            now=NOW,
            nonce="nonce:production:step-up",
        ),
        action_contract=_action(step_up=True),
        effect=BoundaryEffect.seal("integration-effect", lambda action: effects.append(action)),
    )

    assert result.decision.decision == "STEP_UP"
    assert result.effect_committed is False
    assert result.receipt is not None
    assert result.receipt.status == "NOT_COMMITTED"
    assert result.evidence_closure is not None
    assert result.evidence_closure.closed is True
    assert effects == []
