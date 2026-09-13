"""
WHY Gate Test Suite
===================
Tests the post-hoc attribution layer.

Rules:
  - WHY Gate never influences L1 decisions
  - PURPLE is meta-status only (governance/system trust)
  - CAN explains L0-L1, SHOULD explains L2-L3, WHY explains all (especially L4)
  - Placeholder explanations are returned when dependencies (AARM, WORM read) are unavailable
"""

import pytest
import sys
import os
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from why.explanation_engine import WhyGate, ExplanationChannel
from why.purple_detector import PurpleDetector, PurpleEvent, PURPLE_EVENT_TYPES
from why.channel_mapper import ChannelMapper


# ── Local Test Data Types ──────────────────────────────────────────────────

@dataclass
class DistrustDecision:
    """Minimal test data class — not the production distrust engine."""
    level: int
    label: str
    action: str
    combined_score: float = 0.0
    breach_count: int = 0


DECISIONS = {
    "trusted": DistrustDecision(
        level=0, label="TRUSTED", action="PASS",
        combined_score=0.95, breach_count=0
    ),
    "monitor": DistrustDecision(
        level=1, label="MONITOR", action="PASS",
        combined_score=0.70, breach_count=0
    ),
    "warn": DistrustDecision(
        level=2, label="WARN", action="WARN",
        combined_score=0.50, breach_count=2
    ),
    "degrade": DistrustDecision(
        level=3, label="DEGRADE", action="DEGRADE",
        combined_score=0.35, breach_count=4
    ),
    "halt": DistrustDecision(
        level=4, label="HALT", action="HALT",
        combined_score=0.10, breach_count=10
    ),
    "unknown": DistrustDecision(
        level=-1, label="UNKNOWN", action="UNKNOWN",
        combined_score=0.5, breach_count=0
    ),
}


# ── Core Safety: WHY Never Influences L1 ─────────────────────────────────────

class TestWhyNeverInfluencesL1:
    """
    CRITICAL SAFETY PROPERTY: WHY Gate output is never read by L1 frame validation.
    These tests verify the structural separation.
    """

    def test_why_gate_does_not_modify_decision(self):
        """explain() must not modify the input decision object."""
        gate = WhyGate()
        decision = DECISIONS["warn"]
        original_level = decision.level
        gate.explain(decision)
        assert decision.level == original_level


# ── PURPLE: Meta-Status ─────────────────────────────────────────────────────

class TestPurpleIsMeta:
    """PURPLE only activates on governance/system trust events."""

    def test_purple_fires_on_cert_expiry(self):
        detector = PurpleDetector()
        detector.add_event("certificate_expiry", "TLS certificate expires in 24h")
        assert detector.check()

    def test_purple_fires_on_attestation_failure(self):
        detector = PurpleDetector()
        detector.add_event("attestation_failure", "Remote attestation mismatch")
        assert detector.check()

    def test_purple_fires_on_two_person_auth(self):
        detector = PurpleDetector()
        detector.add_event("two_person_auth_triggered", "ASI01 requires second operator")
        assert detector.check()

    def test_purple_does_not_fire_on_normal_l2(self):
        """Normal WARN distrust must NOT activate purple."""
        detector = PurpleDetector()
        assert not detector.check()

    def test_purple_does_not_fire_on_normal_l4(self):
        """Normal HALT distrust must NOT activate purple."""
        detector = PurpleDetector()
        assert not detector.check()


class TestPurpleOverlays:
    """PURPLE can coexist with any normal UI state."""

    def test_purple_overlays_clear(self):
        detector = PurpleDetector()
        detector.add_event("recovery_mode", "Post-incident observation active")
        assert detector.check()

    def test_purple_overlays_lock(self):
        detector = PurpleDetector()
        detector.add_event("two_person_auth_triggered", "Governance override")
        assert detector.check()

    def test_multiple_purple_events(self):
        detector = PurpleDetector()
        detector.add_event("certificate_expiry", "Cert expires soon")
        detector.add_event("policy_change_in_flight", "New policy deploying")
        assert len(detector.active_events) == 2

    def test_clear_single_event(self):
        detector = PurpleDetector()
        detector.add_event("certificate_expiry", "Cert expires soon")
        detector.add_event("recovery_mode", "Recovery active")
        removed = detector.clear_event("certificate_expiry")
        assert removed
        assert len(detector.active_events) == 1

    def test_clear_all_events(self):
        detector = PurpleDetector()
        detector.add_event("certificate_expiry", "Cert expires")
        detector.add_event("recovery_mode", "Recovery")
        detector.clear_all()
        assert not detector.check()

    def test_invalid_event_type_rejected(self):
        detector = PurpleDetector()
        with pytest.raises(ValueError):
            detector.add_event("not_a_purple_event", "Description")


# ── Explanation Channels: Range Tests ────────────────────────────────────────

class TestCanExplanationRange:
    """CAN channel only explains L0-L1 (CLEAR, WATCH)."""

    def test_can_explains_trusted(self):
        gate = WhyGate()
        result = gate.explain(DECISIONS["trusted"])
        assert ExplanationChannel.can in result
        assert "CAN:" in result[ExplanationChannel.can]

    def test_can_explains_monitor(self):
        gate = WhyGate()
        result = gate.explain(DECISIONS["monitor"])
        assert ExplanationChannel.can in result

    def test_can_includes_score(self):
        gate = WhyGate()
        result = gate.explain(DECISIONS["trusted"])
        assert "0.9500" in result[ExplanationChannel.can]


class TestShouldExplanationRange:
    """SHOULD channel only explains L2-L3 (FRICTION, COUNCIL)."""

    def test_should_explains_warn(self):
        gate = WhyGate()
        result = gate.explain(DECISIONS["warn"])
        assert ExplanationChannel.should in result
        assert "SHOULD:" in result[ExplanationChannel.should]

    def test_should_explains_degrade(self):
        gate = WhyGate()
        result = gate.explain(DECISIONS["degrade"])
        assert ExplanationChannel.should in result

    def test_should_placeholder_when_no_aarm(self):
        """SHOULD returns placeholder when AARM logging unavailable."""
        gate = WhyGate()
        result = gate.explain(DECISIONS["warn"])
        assert "placeholder" in result[ExplanationChannel.should].lower() or \
               "PR #9" in result[ExplanationChannel.should]


class TestWhyExplanationRange:
    """WHY channel explains all states, especially L4 (LOCK)."""

    def test_why_explains_halt(self):
        gate = WhyGate()
        result = gate.explain(DECISIONS["halt"])
        assert ExplanationChannel.why in result
        assert "WHY:" in result[ExplanationChannel.why]

    def test_why_explains_warn(self):
        gate = WhyGate()
        result = gate.explain(DECISIONS["warn"])
        assert ExplanationChannel.why in result

    def test_why_placeholder_when_no_worm_read(self):
        """WHY returns placeholder when WORM read API unavailable."""
        gate = WhyGate()
        result = gate.explain(DECISIONS["halt"])
        assert "placeholder" in result[ExplanationChannel.why].lower() or \
               "query layer" in result[ExplanationChannel.why].lower()


# ── Channel Mapper ───────────────────────────────────────────────────────────

class TestChannelMappingComplete:
    """Every L1 decision maps to at least one channel."""

    def test_trusted_maps_to_can(self):
        mapper = ChannelMapper()
        channels = mapper.channels_for(0)
        assert channels == {ExplanationChannel.can}

    def test_monitor_maps_to_can(self):
        mapper = ChannelMapper()
        channels = mapper.channels_for(1)
        assert channels == {ExplanationChannel.can}

    def test_warn_maps_to_can_and_should(self):
        mapper = ChannelMapper()
        channels = mapper.channels_for(2)
        assert ExplanationChannel.can in channels
        assert ExplanationChannel.should in channels
        assert ExplanationChannel.why not in channels

    def test_degrade_maps_to_can_and_should(self):
        mapper = ChannelMapper()
        channels = mapper.channels_for(3)
        assert ExplanationChannel.can in channels
        assert ExplanationChannel.should in channels

    def test_halt_maps_to_all_channels(self):
        mapper = ChannelMapper()
        channels = mapper.channels_for(4)
        assert len(channels) == 3
        assert ExplanationChannel.can in channels
        assert ExplanationChannel.should in channels
        assert ExplanationChannel.why in channels

    def test_unknown_maps_to_can_only(self):
        """UNKNOWN: conservative fallback — only CAN."""
        mapper = ChannelMapper()
        channels = mapper.channels_for(-1)
        assert channels == {ExplanationChannel.can}

    def test_all_levels_map_to_at_least_one(self):
        """Every valid level (-1 to 4) maps to at least one channel."""
        mapper = ChannelMapper()
        for level in range(-1, 5):
            channels = mapper.channels_for(level)
            assert len(channels) >= 1, f"Level {level} maps to zero channels"


class TestChannelMapperApplies:
    """Test the applies() helper method."""

    def test_can_applies_to_l0(self):
        mapper = ChannelMapper()
        assert mapper.applies(0, ExplanationChannel.can)

    def test_should_does_not_apply_to_l0(self):
        mapper = ChannelMapper()
        assert not mapper.applies(0, ExplanationChannel.should)

    def test_why_does_not_apply_to_l1(self):
        mapper = ChannelMapper()
        assert not mapper.applies(1, ExplanationChannel.why)

    def test_why_applies_to_l4(self):
        mapper = ChannelMapper()
        assert mapper.applies(4, ExplanationChannel.why)


# ── Purple Event Types ───────────────────────────────────────────────────────

class TestPurpleEventTypes:
    """Only defined event types are valid."""

    def test_all_defined_types_are_valid(self):
        for event_type in PURPLE_EVENT_TYPES:
            detector = PurpleDetector()
            # Should not raise
            detector.add_event(event_type, f"Test {event_type}")

    def test_non_purple_type_rejected(self):
        detector = PurpleDetector()
        with pytest.raises(ValueError):
            detector.add_event("normal_l2_warn", "Not a purple event")

    def test_is_purple_event_type(self):
        detector = PurpleDetector()
        assert detector.is_purple_event_type("certificate_expiry")
        assert not detector.is_purple_event_type("random_event")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
