from __future__ import annotations

from datetime import timedelta

import pytest

from src.valo_platform.connectors.content import (
    SanityCanaryOperationsError,
    SanityCanaryOperationsStateError,
)
from tests.content_operations.test_sanity_canary_operations import (
    NOW,
    make_runner,
    sanity_case,
    token,
)


def _preflight(runner, *, execution_id: str):
    return runner.preflight(
        action_case=sanity_case(),
        signed_commit_token=token(execution_id),
        integrity_baseline=object(),
        integrity_checkpoint=object(),
        transport=object(),  # type: ignore[arg-type]
        actor_ref="operator:a",
        now=NOW,
    )


def test_halt_persists_only_digest_reference_not_raw_reason(tmp_path) -> None:
    runner, _, _, _, _, store, _ = make_runner(tmp_path)
    raw_reason = "incident token=should-never-enter-operations-state"

    halted = runner.halt(
        actor_ref="operator:a",
        reason=raw_reason,
        now=NOW,
    )

    assert halted.halt_reason is not None
    assert halted.halt_reason.startswith("halt-reason:sha256:")
    assert raw_reason not in halted.halt_reason
    assert raw_reason.encode() not in (tmp_path / "operations.db").read_bytes()
    assert raw_reason not in str(store.events(halted.profile_id))


def test_execute_rejects_preflight_superseded_by_newer_preflight(tmp_path) -> None:
    runner, _, durable, _, _, _, _ = make_runner(tmp_path)
    first = _preflight(runner, execution_id="exec-preflight-first")
    second = _preflight(runner, execution_id="exec-preflight-second")

    assert first.permitted is True
    assert second.permitted is True
    with pytest.raises(SanityCanaryOperationsError, match="latest"):
        runner.execute(
            preflight=first,
            action_case=sanity_case(),
            signed_commit_token=token("exec-preflight-first"),
            integrity_baseline=object(),
            integrity_checkpoint=object(),
            transport=object(),  # type: ignore[arg-type]
            receipt_id="receipt:first",
            now=NOW,
        )

    assert durable.calls == []


def test_operator_references_reject_whitespace_or_control_data(tmp_path) -> None:
    runner, _, _, _, _, _, _ = make_runner(tmp_path)

    with pytest.raises(SanityCanaryOperationsError, match="actor_ref"):
        runner.halt(
            actor_ref="operator with spaces",
            reason="manual stop",
            now=NOW,
        )


def test_halted_same_epoch_cannot_resume_even_with_new_verification_time(tmp_path) -> None:
    runner, _, _, _, _, _, _ = make_runner(tmp_path)
    runner.halt(actor_ref="operator:a", reason="manual stop", now=NOW)

    same = runner.verified_bundle.__class__(
        bundle=runner.verified_bundle.bundle,
        verification_ref=runner.verified_bundle.verification_ref,
        verified_at=NOW + timedelta(minutes=1),
    )
    with pytest.raises(SanityCanaryOperationsStateError, match="newer"):
        runner.resume(
            same,
            actor_ref="operator:b",
            now=NOW + timedelta(minutes=1),
        )
