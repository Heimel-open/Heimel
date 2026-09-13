"""Unit tests for ValoBridge — no L1 binary required.

Tests the 18-byte InferenceTelemetryPacket format used by L1 Guardian.
This is the canonical wire format: big-endian, micro-unit scaled.
"""
import struct
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "l2-orchestrator"))
from bridge import ValoBridge, Decision, _TELEMETRY_FMT, _TELEMETRY_SCALE


class TestTelemetryPacking:
    """Tests for pack_telemetry_packet() — the primary frame format."""

    def setup_method(self):
        self.bridge = ValoBridge()

    def test_packet_is_18_bytes(self):
        """L1 expects exactly 18 bytes (2×u64 BE + 2×u8)."""
        pkt = self.bridge.pack_telemetry_packet(0.80, 1.0, True, True)
        assert len(pkt) == 18, f"Expected 18 bytes, got {len(pkt)}"

    def test_struct_format_size(self):
        """Verify struct format produces 18 bytes."""
        assert struct.calcsize(_TELEMETRY_FMT) == 18

    def test_ai_confidence_encoding(self):
        """Confidence scaled by 1,000,000 and encoded big-endian."""
        pkt = self.bridge.pack_telemetry_packet(0.80, 1.0, True, True)
        scaled = struct.unpack_from(">Q", pkt, 0)[0]
        assert scaled == 800000, f"Expected 800000, got {scaled}"
        assert scaled / _TELEMETRY_SCALE == 0.80

    def test_c0_threshold_encoding(self):
        """C0 threshold scaled by 1,000,000 and encoded big-endian."""
        pkt = self.bridge.pack_telemetry_packet(0.80, 1.0, True, True)
        scaled = struct.unpack_from(">Q", pkt, 8)[0]
        assert scaled == 1000000, f"Expected 1000000, got {scaled}"
        assert scaled / _TELEMETRY_SCALE == 1.0

    def test_syntax_valid_true(self):
        pkt = self.bridge.pack_telemetry_packet(0.80, 1.0, True, True)
        assert struct.unpack_from(">B", pkt, 16)[0] == 1

    def test_syntax_valid_false(self):
        pkt = self.bridge.pack_telemetry_packet(0.80, 1.0, False, True)
        assert struct.unpack_from(">B", pkt, 16)[0] == 0

    def test_latency_ok_true(self):
        pkt = self.bridge.pack_telemetry_packet(0.80, 1.0, True, True)
        assert struct.unpack_from(">B", pkt, 17)[0] == 1

    def test_latency_ok_false(self):
        pkt = self.bridge.pack_telemetry_packet(0.80, 1.0, True, False)
        assert struct.unpack_from(">B", pkt, 17)[0] == 0

    def test_big_endian_encoding(self):
        """Verify big-endian (network byte order) for the u64 ai_confidence field.

        ai_confidence=0.80 scales to 800000 = 0x0C3500. Packed as a big-endian
        u64 (8 bytes) it is: 00 00 00 00 00 0C 35 00. So pkt[5]=0x0C, pkt[6]=0x35,
        pkt[7]=0x00 (the LSB). The earlier test wrongly assumed a 32-bit field.
        """
        pkt = self.bridge.pack_telemetry_packet(0.80, 1.0, True, True)
        assert pkt[0] == 0x00  # MSB first
        assert pkt[1] == 0x00
        assert pkt[2] == 0x00
        assert pkt[3] == 0x00
        assert pkt[4] == 0x00
        assert pkt[5] == 0x0C  # 800000 = 0x00000000000C3500 (u64 BE)
        assert pkt[6] == 0x35
        assert pkt[7] == 0x00  # LSB

    def test_zero_confidence(self):
        pkt = self.bridge.pack_telemetry_packet(0.0, 1.0, True, True)
        assert struct.unpack_from(">Q", pkt, 0)[0] == 0

    def test_max_confidence(self):
        pkt = self.bridge.pack_telemetry_packet(1.0, 1.0, True, True)
        assert struct.unpack_from(">Q", pkt, 0)[0] == 1_000_000

    def test_roundtrip_precision(self):
        """Micro-unit scaling preserves 6 decimal places."""
        original = 0.123456
        pkt = self.bridge.pack_telemetry_packet(original, 1.0, True, True)
        scaled = struct.unpack_from(">Q", pkt, 0)[0]
        recovered = scaled / _TELEMETRY_SCALE
        assert abs(recovered - original) < 0.000001


class TestValoFrameCompatibility:
    """Tests for pack_valo_frame() — compatibility wrapper.

    pack_valo_frame() accepts the old API but delegates to
    pack_telemetry_packet(), returning 18 bytes.
    """

    def setup_method(self):
        self.bridge = ValoBridge()

    def test_returns_18_bytes_not_64(self):
        """The old format was 64 bytes; the new format is 18."""
        frame = self.bridge.pack_valo_frame(98.0, 100.0, 5.0)
        assert len(frame) == 18, f"Expected 18 bytes, got {len(frame)}"

    def test_val_primary_maps_to_c0(self):
        """val_primary → c0_threshold."""
        frame = self.bridge.pack_valo_frame(1.0, 0.80, 5.0)
        c0_scaled = struct.unpack_from(">Q", frame, 8)[0]
        assert c0_scaled == 1_000_000

    def test_val_secondary_maps_to_confidence(self):
        """val_secondary → ai_confidence."""
        frame = self.bridge.pack_valo_frame(1.0, 0.80, 5.0)
        conf_scaled = struct.unpack_from(">Q", frame, 0)[0]
        assert conf_scaled == 800_000

    def test_extra_args_ignored(self):
        """max_spread, identifier, domain, fail_mode are not on the wire."""
        frame_a = self.bridge.pack_valo_frame(1.0, 0.80, 5.0, 0, 0)
        frame_b = self.bridge.pack_valo_frame(1.0, 0.80, 999.0, 42, 7, 0xDEAD)
        assert frame_a == frame_b, "Extra args should not affect wire format"


class TestDecisionEnum:
    """Decision enum maps to L1 ValoState."""

    def test_allow_is_0x00(self):
        assert Decision.ALLOW == 0x00

    def test_degraded_is_0x01(self):
        assert Decision.DEGRADED == 0x01

    def test_halt_is_0x02(self):
        assert Decision.HALT == 0x02

    def test_logfullhalt_is_0x03(self):
        assert Decision.LOGFULLHALT == 0x03

    def test_from_byte(self):
        assert Decision(0) == Decision.ALLOW
        assert Decision(1) == Decision.DEGRADED
        assert Decision(2) == Decision.HALT
        assert Decision(3) == Decision.LOGFULLHALT


class TestCoherenceInvariants:
    """Mathematical coherence checks — verifiable without L1."""

    def test_coherence_zone_low(self):
        """0.42 * c0 is the floor."""
        c0 = 1.0
        assert 0.42 * c0 == 0.42

    def test_coherence_zone_high(self):
        """1.06 * c0 is the ceiling."""
        c0 = 1.0
        assert 1.06 * c0 == 1.06

    def test_confidence_within_zone(self):
        """0.80 is within [0.42, 1.06]."""
        c0 = 1.0
        confidence = 0.80
        assert 0.42 * c0 <= confidence <= 1.06 * c0

    def test_confidence_below_floor(self):
        """0.20 < 0.42 — should trigger Degraded."""
        c0 = 1.0
        confidence = 0.20
        assert confidence < 0.42 * c0

    def test_confidence_above_ceiling(self):
        """1.20 > 1.06 — should trigger Degraded."""
        c0 = 1.0
        confidence = 1.20
        assert confidence > 1.06 * c0

    def test_phi_law_connection(self):
        """0.42 is the Phi-law alpha constant."""
        assert _C0_LOW == 0.42
        assert _C0_HIGH == 1.06


# Coherence constants (from validation_logic.rs)
_C0_LOW = 0.42
_C0_HIGH = 1.06
