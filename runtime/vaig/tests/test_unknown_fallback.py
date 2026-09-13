"""
UNKNOWN Fallback Test Suite
============================
Tests conservative fallback semantics: UNKNOWN != SAFE.

Rule: When the system cannot determine a known distrust level,
      it must HALT. Never PASS. Never proceed with undefined state.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from why.unknown_fallback import (
    apply_fallback, is_valid_level, VALID_LEVELS,
    UNKNOWN_FALLBACK, FallbackDecision
)


# ── Valid Levels: Pass Through ───────────────────────────────────────────────

class TestValidLevelsPassThrough:
    """Valid levels (0-4) must pass through unchanged."""

    def test_trusted_passthrough(self):
        result = apply_fallback(0)
        assert result.effective_level == 0
        assert result.label == "TRUSTED"
        assert result.action == "PASS"
        assert not result.was_unknown

    def test_monitor_passthrough(self):
        result = apply_fallback(1)
        assert result.effective_level == 1
        assert result.label == "MONITOR"
        assert result.action == "PASS"
        assert not result.was_unknown

    def test_warn_passthrough(self):
        result = apply_fallback(2)
        assert result.effective_level == 2
        assert result.label == "WARN"
        assert result.action == "WARN"
        assert not result.was_unknown

    def test_degrade_passthrough(self):
        result = apply_fallback(3)
        assert result.effective_level == 3
        assert result.label == "DEGRADE"
        assert result.action == "DEGRADE"
        assert not result.was_unknown

    def test_halt_passthrough(self):
        result = apply_fallback(4)
        assert result.effective_level == 4
        assert result.label == "HALT"
        assert result.action == "HALT"
        assert not result.was_unknown


# ── UNKNOWN: Conservative HALT ───────────────────────────────────────────────

class TestUnknownHalts:
    """
    CRITICAL SAFETY PROPERTY: Unknown levels must produce HALT.
    This is the core UNKNOWN != SAFE rule.
    """

    def test_negative_one_halts(self):
        """level=-1 (common error value) must HALT."""
        result = apply_fallback(-1)
        assert result.was_unknown
        assert result.effective_level == 4
        assert result.action == "HALT"

    def test_level_five_halts(self):
        """level=5 (future level, unknown to current code) must HALT."""
        result = apply_fallback(5)
        assert result.was_unknown
        assert result.effective_level == 4
        assert result.action == "HALT"

    def test_large_invalid_level_halts(self):
        """level=999 (corrupted value) must HALT."""
        result = apply_fallback(999)
        assert result.was_unknown
        assert result.effective_level == 4
        assert result.action == "HALT"

    def test_none_equivalent_halts(self):
        """level=-999 (extreme negative) must HALT."""
        result = apply_fallback(-999)
        assert result.was_unknown
        assert result.effective_level == 4

    def test_unknown_label_preserved(self):
        """The original label shows UNKNOWN but action is HALT."""
        result = apply_fallback(-1)
        assert result.label == "UNKNOWN"
        assert result.action == "HALT"

    def test_unknown_reason_documented(self):
        """Unknown decisions include a reason string."""
        result = apply_fallback(-1)
        assert "conservative" in result.reason.lower() or "unknown" in result.reason.lower()


# ── Boundary Cases ───────────────────────────────────────────────────────────

class TestBoundaryCases:
    """Edge cases around the valid/invalid boundary."""

    def test_all_valid_levels_accepted(self):
        """Every level in VALID_LEVELS must pass through."""
        for level in VALID_LEVELS:
            result = apply_fallback(level)
            assert not result.was_unknown, f"Level {level} was incorrectly flagged as unknown"

    def test_zero_is_valid(self):
        """Level 0 (TRUSTED) is valid."""
        assert is_valid_level(0)

    def test_four_is_valid(self):
        """Level 4 (HALT) is valid."""
        assert is_valid_level(4)

    def test_minus_one_is_invalid(self):
        """Level -1 is invalid."""
        assert not is_valid_level(-1)

    def test_five_is_invalid(self):
        """Level 5 is invalid (not in current spec)."""
        assert not is_valid_level(5)


# ── Custom Label/Action Preservation ─────────────────────────────────────────

class TestCustomLabelAction:
    """When valid level with custom label/action is provided, preserve them."""

    def test_custom_label_preserved(self):
        result = apply_fallback(2, label="CUSTOM_WARN", action="CUSTOM")
        assert result.label == "CUSTOM_WARN"
        assert result.action == "CUSTOM"

    def test_unknown_ignores_custom_action(self):
        """Unknown level: action is always HALT regardless of input."""
        result = apply_fallback(-1, label="CUSTOM", action="PASS")
        assert result.was_unknown
        assert result.action == "HALT"  # Conservative: always HALT


# ── Safety Invariants ────────────────────────────────────────────────────────

class TestSafetyInvariants:
    """Properties that must hold for all inputs."""

    def test_effective_level_always_in_range(self):
        """effective_level is always 0-4, never outside."""
        test_levels = [-999, -1, 0, 1, 2, 3, 4, 5, 999]
        for level in test_levels:
            result = apply_fallback(level)
            assert 0 <= result.effective_level <= 4

    def test_action_never_empty(self):
        """action is never empty string."""
        for level in [-1, 0, 2, 4, 99]:
            result = apply_fallback(level)
            assert result.action != ""
            assert result.action != "UNKNOWN"  # Must resolve to concrete action

    def test_unknown_always_halts(self):
        """For ALL invalid levels, action == HALT."""
        invalid_levels = [-100, -1, 5, 6, 10, 100, 1000]
        for level in invalid_levels:
            result = apply_fallback(level)
            assert result.action == "HALT", f"Level {level} did not HALT"

    def test_was_unknown_flag_set_correctly(self):
        """was_unknown is True only for invalid levels."""
        for level in VALID_LEVELS:
            assert not apply_fallback(level).was_unknown
        assert apply_fallback(-1).was_unknown
        assert apply_fallback(5).was_unknown

    def test_fallback_decision_has_timestamp(self):
        """All decisions have a timestamp."""
        result = apply_fallback(0)
        assert result.timestamp > 0


# ── Constants ────────────────────────────────────────────────────────────────

class TestConstants:
    """Verify module-level constants."""

    def test_valid_levels_set(self):
        assert VALID_LEVELS == {0, 1, 2, 3, 4}

    def test_unknown_fallback_structure(self):
        assert UNKNOWN_FALLBACK["level"] == 4
        assert UNKNOWN_FALLBACK["action"] == "HALT"
        assert "unknown" in UNKNOWN_FALLBACK["label"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
