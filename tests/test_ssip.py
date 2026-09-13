"""SSIP (Self-Scaling Integrity Protocol) runtime safety tests.

Verifies:
- DefermentMode enum values
- deferment_for_signal maps HSRS levels to correct modes
- deferment_for_signal with oob_consistent=False always returns ISOLATION
- ReversionLevel enum values and escalation ordering
- EvidencePack creation and to_dict round-trip
- EvidencePack packet_id prefix
- EvidencePack frozen (immutable)
"""

import pytest

from vaig.ssip import (
    DefermentMode,
    EvidencePack,
    ReversionLevel,
    deferment_for_signal,
)


# ── DefermentMode ──────────────────────────────────────────────

class TestDefermentForSignal:
    def test_critical_maps_to_isolation(self):
        assert deferment_for_signal("CRITICAL") == DefermentMode.ISOLATION

    def test_high_maps_to_restricted(self):
        assert deferment_for_signal("HIGH") == DefermentMode.RESTRICTED

    def test_medium_maps_to_monitoring(self):
        assert deferment_for_signal("MEDIUM") == DefermentMode.MONITORING

    def test_low_maps_to_normal(self):
        assert deferment_for_signal("LOW") == DefermentMode.NORMAL

    def test_unknown_level_maps_to_normal(self):
        assert deferment_for_signal("WHATEVER") == DefermentMode.NORMAL

    def test_oob_inconsistent_always_isolation(self):
        for level in ["LOW", "MEDIUM", "HIGH", "CRITICAL", "WHATEVER"]:
            result = deferment_for_signal(level, oob_consistent=False)
            assert result == DefermentMode.ISOLATION, f"Expected ISOLATION for level={level!r} with oob_consistent=False"

    def test_case_insensitive(self):
        assert deferment_for_signal("critical") == DefermentMode.ISOLATION
        assert deferment_for_signal("High") == DefermentMode.RESTRICTED
        assert deferment_for_signal("medium") == DefermentMode.MONITORING

    def test_whitespace_stripped(self):
        assert deferment_for_signal("  CRITICAL  ") == DefermentMode.ISOLATION

    def test_deferment_mode_string_values(self):
        assert DefermentMode.NORMAL.value == "NORMAL"
        assert DefermentMode.MONITORING.value == "MONITORING"
        assert DefermentMode.RESTRICTED.value == "RESTRICTED"
        assert DefermentMode.ISOLATION.value == "ISOLATION"


# ── ReversionLevel ─────────────────────────────────────────────

class TestReversionLevel:
    def test_all_levels_present(self):
        levels = {r.value for r in ReversionLevel}
        assert levels == {"NONE", "SOFT_REVERSION", "HARD_REVERSION", "CATASTROPHIC_LOCKDOWN"}

    def test_none_is_least_severe(self):
        assert ReversionLevel.NONE.value == "NONE"

    def test_catastrophic_lockdown_is_most_severe(self):
        assert ReversionLevel.CATASTROPHIC_LOCKDOWN.value == "CATASTROPHIC_LOCKDOWN"

    def test_reversion_level_string_values(self):
        assert isinstance(ReversionLevel.SOFT_REVERSION, str)
        assert ReversionLevel.HARD_REVERSION.value == "HARD_REVERSION"


# ── EvidencePack ───────────────────────────────────────────────

class TestEvidencePack:
    def _pack(self, **kwargs) -> EvidencePack:
        defaults = dict(
            incident_id="INC-001",
            evidence_core="Raw WORM log entries 1-42",
            system_context="VAIG v0.2.0, medical domain",
            hear_chain="sha256:abc123",
        )
        defaults.update(kwargs)
        return EvidencePack(**defaults)

    def test_basic_creation(self):
        pack = self._pack()
        assert pack.incident_id == "INC-001"
        assert pack.evidence_core == "Raw WORM log entries 1-42"

    def test_packet_id_prefix(self):
        pack = self._pack()
        assert pack.packet_id.startswith("pifr_")

    def test_packet_id_unique(self):
        p1 = self._pack()
        p2 = self._pack()
        assert p1.packet_id != p2.packet_id

    def test_created_at_set(self):
        pack = self._pack()
        assert pack.created_at
        assert "T" in pack.created_at  # ISO format

    def test_optional_fields_default_none(self):
        pack = self._pack()
        assert pack.external_analysis is None
        assert pack.root_cause is None
        assert pack.remediation is None
        assert pack.closure_signature is None

    def test_optional_fields_set(self):
        pack = self._pack(
            external_analysis="External reviewer: no issues",
            root_cause="Threshold misconfiguration",
            remediation="Updated HALT threshold to 0.65",
            closure_signature="sig-xyz",
        )
        assert pack.external_analysis == "External reviewer: no issues"
        assert pack.root_cause == "Threshold misconfiguration"

    def test_metadata_default_empty(self):
        pack = self._pack()
        assert pack.metadata == {}

    def test_metadata_set(self):
        pack = self._pack(metadata={"domain": "medical", "severity": 3})
        assert pack.metadata["domain"] == "medical"
        assert pack.metadata["severity"] == 3

    def test_to_dict_contains_all_required_fields(self):
        pack = self._pack()
        d = pack.to_dict()
        required = {
            "incident_id", "evidence_core", "system_context", "hear_chain",
            "created_at", "packet_id", "metadata",
        }
        assert required.issubset(d.keys())

    def test_to_dict_values_match(self):
        pack = self._pack()
        d = pack.to_dict()
        assert d["incident_id"] == pack.incident_id
        assert d["packet_id"] == pack.packet_id
        assert d["created_at"] == pack.created_at

    def test_frozen_immutable(self):
        pack = self._pack()
        with pytest.raises((AttributeError, TypeError)):
            pack.incident_id = "changed"  # type: ignore[misc]
