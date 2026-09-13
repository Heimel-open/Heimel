"""
Tests for management_overlay: CAN/SHOULD/WHY aggregation and status display.

Spec: docs/can-should-why-vu-meter.md
Run: pytest tests/test_management_overlay.py -v
"""
import pytest
from vaig.management_overlay.signals.can_should_why import (
    SignalLevel,
    OverlaySignals,
    aggregate,
)
from vaig.management_overlay.api.status import OverlayStatus, render_compact, render_expanded


class TestSignalLevel:
    def test_ordering(self):
        assert SignalLevel.GREEN < SignalLevel.YELLOW < SignalLevel.ORANGE < SignalLevel.RED < SignalLevel.PURPLE

    def test_green_not_blocked(self):
        assert not SignalLevel.GREEN.is_consequence_blocked

    def test_red_is_blocked(self):
        assert SignalLevel.RED.is_consequence_blocked

    def test_purple_is_blocked(self):
        assert SignalLevel.PURPLE.is_consequence_blocked

    def test_yellow_not_blocked(self):
        assert not SignalLevel.YELLOW.is_consequence_blocked


class TestAggregation:
    def test_all_green_is_green(self):
        s = OverlaySignals(can=SignalLevel.GREEN, should=SignalLevel.GREEN, why=SignalLevel.GREEN)
        assert aggregate(s) == SignalLevel.GREEN

    def test_weakest_link_why(self):
        """High CAN + high SHOULD + low WHY is still unsafe — weakest link wins."""
        s = OverlaySignals(can=SignalLevel.GREEN, should=SignalLevel.GREEN, why=SignalLevel.ORANGE)
        assert aggregate(s) == SignalLevel.ORANGE

    def test_weakest_link_can(self):
        s = OverlaySignals(can=SignalLevel.RED, should=SignalLevel.GREEN, why=SignalLevel.GREEN)
        assert aggregate(s) == SignalLevel.RED

    def test_weakest_link_should(self):
        s = OverlaySignals(can=SignalLevel.YELLOW, should=SignalLevel.RED, why=SignalLevel.YELLOW)
        assert aggregate(s) == SignalLevel.RED

    def test_purple_override_worm_degraded(self):
        """WORM degradation → PURPLE regardless of CAN/SHOULD/WHY."""
        s = OverlaySignals(
            can=SignalLevel.GREEN,
            should=SignalLevel.GREEN,
            why=SignalLevel.GREEN,
            worm_ok=False,
        )
        assert aggregate(s) == SignalLevel.PURPLE

    def test_purple_override_ssip_degraded(self):
        s = OverlaySignals(
            can=SignalLevel.GREEN,
            should=SignalLevel.GREEN,
            why=SignalLevel.GREEN,
            ssip_ok=False,
        )
        assert aggregate(s) == SignalLevel.PURPLE

    def test_purple_override_beats_red(self):
        """Even RED CAN/SHOULD/WHY becomes PURPLE when integrity degraded."""
        s = OverlaySignals(
            can=SignalLevel.RED,
            should=SignalLevel.RED,
            why=SignalLevel.RED,
            worm_ok=False,
        )
        assert aggregate(s) == SignalLevel.PURPLE

    def test_all_nominal_worm_ssip_ok(self):
        s = OverlaySignals(worm_ok=True, ssip_ok=True)
        assert aggregate(s) == SignalLevel.GREEN

    def test_orange_why_triggers_human_review(self):
        s = OverlaySignals(why=SignalLevel.ORANGE)
        status = OverlayStatus.compute(s)
        assert status.requires_human_review

    def test_yellow_does_not_require_human_review(self):
        s = OverlaySignals(why=SignalLevel.YELLOW)
        status = OverlayStatus.compute(s)
        assert not status.requires_human_review


class TestOverlayStatus:
    def test_compute_sets_overall(self):
        s = OverlaySignals(why=SignalLevel.ORANGE)
        status = OverlayStatus.compute(s)
        assert status.overall == SignalLevel.ORANGE

    def test_consequence_commitment_enabled_for_green(self):
        s = OverlaySignals()
        status = OverlayStatus.compute(s)
        assert status.consequence_commitment_enabled

    def test_consequence_commitment_disabled_for_red(self):
        s = OverlaySignals(can=SignalLevel.RED)
        status = OverlayStatus.compute(s)
        assert not status.consequence_commitment_enabled

    def test_consequence_commitment_disabled_for_purple(self):
        s = OverlaySignals(worm_ok=False)
        status = OverlayStatus.compute(s)
        assert not status.consequence_commitment_enabled

    def test_receipt_hash_stored(self):
        s = OverlaySignals()
        status = OverlayStatus.compute(s, receipt_hash="abc123")
        assert status.receipt_hash == "abc123"


class TestRenderCompact:
    def test_green_status_line(self):
        s = OverlaySignals()
        status = OverlayStatus.compute(s)
        output = render_compact(status)
        assert "GREEN" in output
        assert "VALO:" in output

    def test_orange_status_line(self):
        s = OverlaySignals(why=SignalLevel.ORANGE, reason="WHY continuity degraded")
        status = OverlayStatus.compute(s)
        output = render_compact(status)
        assert "ORANGE" in output
        assert "WHY continuity degraded" in output

    def test_receipt_hash_truncated(self):
        s = OverlaySignals()
        status = OverlayStatus.compute(s, receipt_hash="deadbeef" * 8)
        output = render_compact(status)
        assert "WORM hash" in output


class TestRenderExpanded:
    def test_expanded_shows_three_signals(self):
        s = OverlaySignals(why=SignalLevel.ORANGE, reason="WHY continuity below threshold")
        status = OverlayStatus.compute(s)
        output = render_expanded(status)
        assert "CAN" in output
        assert "SHOULD" in output
        assert "WHY" in output
        assert "ORANGE" in output

    def test_purple_display_disables_commitment(self):
        s = OverlaySignals(worm_ok=False, reason="WORM chain broken")
        status = OverlayStatus.compute(s)
        output = render_expanded(status)
        assert "PURPLE" in output
        assert "DISABLED" in output
        assert "PRESERVED" in output

    def test_red_display_shows_halt(self):
        s = OverlaySignals(can=SignalLevel.RED)
        status = OverlayStatus.compute(s)
        output = render_expanded(status)
        assert "RED" in output
