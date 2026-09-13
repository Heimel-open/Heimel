from __future__ import annotations

from datetime import UTC, datetime
import sys
from pathlib import Path

from heimel_runtime import HeimelRuntime

sys.path.insert(0, str(Path(__file__).parents[3] / "runtime" / "reht" / "tests"))
from two_core_harness import (  # noqa: E402
    CAPABILITY,
    PURPOSE,
    TARGET,
    _revoke_event,
    base_engine,
    build_context,
)


NOW = datetime(2026, 8, 23, 18, 55, tzinfo=UTC)


def _action() -> dict[str, str]:
    return {
        "action_id": "action:heimel-runtime",
        "capability": CAPABILITY,
        "target": TARGET,
        "action_type": CAPABILITY,
        "purpose_id": PURPOSE,
    }


def test_production_runtime_closes_the_full_consequence_chain(tmp_path) -> None:
    engine = base_engine(now=NOW)
    runtime = HeimelRuntime.production(engine, tmp_path)
    action = _action()
    effects: list[dict[str, str]] = []

    execution = runtime.execute(
        context_factory=lambda requested: build_context(
            engine, requested, now=NOW, nonce="nonce:heimel-runtime"
        ),
        action_contract=action,
        effect_name="heimel-test-effect",
        effect=lambda requested: effects.append(requested) or {"ok": True},
    )

    assert execution.committed is True
    assert execution.evidence_closed is True
    assert effects == [action]
    assert runtime.ledger.worm.verify() is True
    assert len(engine.events()) > 0


def test_production_runtime_denies_revoked_authority_without_effect(tmp_path) -> None:
    engine = base_engine(now=NOW)
    engine.append(_revoke_event(now=NOW))
    runtime = HeimelRuntime.production(engine, tmp_path)
    effects: list[dict[str, str]] = []

    execution = runtime.execute(
        context_factory=lambda requested: build_context(
            engine, requested, now=NOW, nonce="nonce:heimel-revoked"
        ),
        action_contract=_action(),
        effect_name="must-not-run",
        effect=lambda requested: effects.append(requested),
    )

    assert execution.committed is False
    assert execution.result.decision.decision == "DENY"
    assert effects == []
    assert execution.evidence_closed is True
