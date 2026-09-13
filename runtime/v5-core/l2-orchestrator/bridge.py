# VALO V5.0 - L2 Orchestrator Bridge
# Transport-agnostic, observability-integrated, thread-safe

import struct
from datetime import datetime, timezone
from enum import IntEnum
from typing import Optional

from codec import Transport
from observability import log_decision, log_halt


class Decision(IntEnum):
    ALLOW       = 0x00  # ValoState::Active
    DEGRADED    = 0x01  # ValoState::Degraded
    HALT        = 0x02  # ValoState::Halt
    LOGFULLHALT = 0x03  # ValoState::LogFullHalt


# InferenceTelemetryPacket layout (18 bytes, big-endian):
#   0   8   ai_confidence_scaled  u64 BE  (ai_confidence * 1_000_000)
#   8   8   c0_threshold_scaled   u64 BE  (c0_threshold  * 1_000_000)
#  16   1   syntax_valid_flag     u8      (1=valid, 0=invalid)
#  17   1   latency_ok_flag       u8      (1=ok,    0=too slow)
_TELEMETRY_FMT = ">QQBB"
_TELEMETRY_SCALE = 1_000_000
assert struct.calcsize(_TELEMETRY_FMT) == 18


class ValoBridge:
    """
    L2 Orchestrator Bridge — Protocol-agnostic via Transport strategy.

    Responsibilities:
    - Pack frames for L1 Guardian (18-byte InferenceTelemetryPacket)
    - Send/receive via pluggable Transport
    - Log decisions for audit trail
    - Return Decision + RTT

    Transport is injected; no direct socket access.
    Thread-safe via StructuredLogger._lock.

    Wire format: L1 Guardian accepts 18-byte InferenceTelemetryPacket.
    pack_valo_frame() is a compatibility wrapper for callers that use the
    val_primary/val_secondary naming convention (e.g. vaig.py, janus_integration.py).
    """

    def __init__(self, transport: Optional[Transport] = None):
        self.transport = transport
        self._distrust_level = 0  # Updated by L3 context (optional)

    def connect(self, config: dict) -> None:
        """
        Establish connection via transport.

        Args:
            config (dict): Transport-specific config
                TCP:  {"host": "127.0.0.1", "port": 7743}
                UDS:  {"path": "/tmp/valo_v5_l1.sock"}
        """
        if self.transport is None:
            raise RuntimeError("Transport not initialized. Pass transport to __init__().")
        self.transport.connect(config)

    def connect_uds(self, path: str) -> None:
        """Convenience wrapper: establish UDS connection."""
        self.connect({"path": path})

    def pack_telemetry_packet(
        self,
        ai_confidence: float,
        c0_threshold: float,
        syntax_valid: bool = True,
        latency_ok: bool = True,
    ) -> bytes:
        """
        Pack an 18-byte InferenceTelemetryPacket for L1 Guardian.

        This is the primary frame format accepted by the L1 Rust server.
        """
        conf_scaled = int(ai_confidence * _TELEMETRY_SCALE)
        c0_scaled = int(c0_threshold * _TELEMETRY_SCALE)
        return struct.pack(
            _TELEMETRY_FMT,
            conf_scaled,
            c0_scaled,
            1 if syntax_valid else 0,
            1 if latency_ok else 0,
        )

    def pack_valo_frame(
        self,
        val_primary: float,
        val_secondary: float,
        max_spread: float,
        identifier: int = 0,
        domain: int = 0,
        fail_mode: int = 0,
    ) -> bytes:
        """
        Compatibility wrapper for VAIG/JANUS callers using val_primary/val_secondary naming.

        Mapping to L1 InferenceTelemetryPacket:
            val_secondary → ai_confidence  (the LLM output confidence score)
            val_primary   → c0_threshold   (the configured coherence threshold)

        max_spread, identifier, domain, fail_mode are not part of the wire protocol;
        they are accepted for API compatibility but not forwarded to L1.
        """
        return self.pack_telemetry_packet(
            ai_confidence=val_secondary,
            c0_threshold=val_primary,
            syntax_valid=True,
            latency_ok=True,
        )

    def send_frame(self, frame: bytes) -> tuple:
        """
        Send packet to L1, receive decision.

        Args:
            frame (bytes): 18-byte InferenceTelemetryPacket (from pack_telemetry_packet
                           or pack_valo_frame)

        Returns:
            Tuple[Decision, int]: (decision, round_trip_ns)
        """
        if self.transport is None:
            raise RuntimeError("Transport not initialized")

        # Extract ai_confidence for logging (unscale from big-endian u64)
        conf_scaled, c0_scaled, syntax_flag, latency_flag = struct.unpack_from(_TELEMETRY_FMT, frame, 0)
        ai_confidence = conf_scaled / _TELEMETRY_SCALE
        c0_threshold = c0_scaled / _TELEMETRY_SCALE

        try:
            resp, rtt_ns = self.transport.send_recv(frame)
        except ConnectionError as e:
            log_halt(
                frame_id=0,
                val_primary=c0_threshold,
                val_secondary=ai_confidence,
                max_spread=0.0,
                reason=f"TRANSPORT_ERROR: {str(e)}",
                distrust_level=self._distrust_level,
            )
            raise

        decision = Decision(resp[0])
        rtt_us = rtt_ns / 1000.0

        log_decision(decision.name, 0, rtt_us, self._distrust_level)

        if decision == Decision.HALT:
            log_halt(
                frame_id=0,
                val_primary=c0_threshold,
                val_secondary=ai_confidence,
                max_spread=0.0,
                reason="DECISION_HALT_FROM_L1",
                distrust_level=self._distrust_level,
            )

        return decision, rtt_ns

    def set_distrust_level(self, level: int) -> None:
        """Update distrust level from L3 context (affects log context only)."""
        self._distrust_level = min(max(level, 0), 4)

    def close(self) -> None:
        """Cleanly close transport."""
        if self.transport:
            self.transport.close()
