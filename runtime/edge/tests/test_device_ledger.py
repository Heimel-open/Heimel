"""Tests for the embedded device governance vertikal."""

import pytest

from valo_edge.device import DeviceActionOutcome, DeviceGovernanceLedger
from valo_edge.governance import MicroSignal, SignalDisposition


def _ok_signal():
    return [MicroSignal("sensor", SignalDisposition.OK, confidence=0.9)]


def test_full_allowed_pipeline():
    ledger = DeviceGovernanceLedger("dev-1", rate_limit_per_min=10)
    ledger.grant_consent("actuate", "motor", "2026-08-06T00:00:00Z")
    result = ledger.evaluate(
        action_type="actuate_motor",
        parameters={"speed": 100},
        purpose="actuate",
        signals=_ok_signal(),
        now_iso="2026-08-06T00:01:00Z",
    )
    assert result.outcome is DeviceActionOutcome.ALLOWED
    assert result.worm_hash
    assert ledger.verify()


def test_blocks_without_consent():
    ledger = DeviceGovernanceLedger("dev-1")
    result = ledger.evaluate(
        action_type="actuate",
        parameters={},
        purpose="sensitive",
        signals=_ok_signal(),
        now_iso="2026-08-06T00:01:00Z",
    )
    assert result.outcome is DeviceActionOutcome.BLOCKED_NO_CONSENT


def test_blocks_on_admissibility():
    ledger = DeviceGovernanceLedger("dev-1")
    ledger.grant_consent("actuate", "motor", "2026-08-06T00:00:00Z")
    result = ledger.evaluate(
        action_type="actuate",
        parameters={},
        purpose="actuate",
        signals=[MicroSignal("safety", SignalDisposition.BLOCK, confidence=0.9)],
        now_iso="2026-08-06T00:01:00Z",
    )
    assert result.outcome is DeviceActionOutcome.BLOCKED_ADMISSIBILITY


def test_blocks_on_rate_limit():
    ledger = DeviceGovernanceLedger("dev-1", rate_limit_per_min=1)
    ledger.grant_consent("actuate", "motor", "2026-08-06T00:00:00Z")
    ledger.evaluate(
        action_type="a", parameters={}, purpose="actuate",
        signals=_ok_signal(), now_iso="2026-08-06T00:01:00Z",
    )
    result = ledger.evaluate(
        action_type="b", parameters={}, purpose="actuate",
        signals=_ok_signal(), now_iso="2026-08-06T00:01:01Z",
    )
    assert result.outcome is DeviceActionOutcome.BLOCKED_RATE


def test_blocks_on_revocation():
    ledger = DeviceGovernanceLedger("dev-1")
    ledger.grant_consent("actuate", "motor", "2026-08-06T00:00:00Z")
    assert ledger.revoke_device("guardian", "sig")
    result = ledger.evaluate(
        action_type="a", parameters={}, purpose="actuate",
        signals=_ok_signal(), now_iso="2026-08-06T00:01:00Z",
    )
    assert result.outcome is DeviceActionOutcome.BLOCKED_REVOKED


def test_blocks_on_halt():
    ledger = DeviceGovernanceLedger("dev-1")
    ledger.grant_consent("actuate", "motor", "2026-08-06T00:00:00Z")
    ledger.trigger_halt("emergency")
    result = ledger.evaluate(
        action_type="a", parameters={}, purpose="actuate",
        signals=_ok_signal(), now_iso="2026-08-06T00:01:00Z",
    )
    assert result.outcome is DeviceActionOutcome.BLOCKED_HALT
