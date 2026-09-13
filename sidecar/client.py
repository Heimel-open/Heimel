import os
import socket
import struct
import time

# VALO is a sidecar — the application continues if VALO is unreachable.
# UDS is preferred for same-host (lower overhead); TCP is the fallback.

BYPASS_MODE = "BYPASS_MODE"
UDS_PATH = "/tmp/valo_v5_l1.sock"
TCP_HOST = "127.0.0.1"
TCP_PORT = 7743

# L1 expects 18-byte InferenceTelemetryPacket:
#   u64 BE: ai_confidence_scaled  (confidence * 1_000_000)
#   u64 BE: c0_threshold_scaled   (threshold * 1_000_000)
#   u8:     syntax_valid_flag     (1=valid, 0=invalid)
#   u8:     latency_ok_flag       (1=ok, 0=too slow)
_TELEMETRY_FMT = ">QQBB"
_TELEMETRY_SCALE = 1_000_000


class ValoSidecarClient:
    """Lightweight validation client for application integration.

    Communicates with L1 Guardian using the canonical 18-byte
    InferenceTelemetryPacket format (big-endian, micro-unit scaling).
    """

    def __init__(self, tcp_host: str = TCP_HOST, tcp_port: int = TCP_PORT):
        self.tcp_host = tcp_host
        self.tcp_port = tcp_port

    def _uds_available(self) -> bool:
        return os.path.exists(UDS_PATH)

    def request_validation(self, primary_val: float, secondary_val: float) -> str:
        """
        Validate a (primary, secondary) pair via L1.
        Returns "ALLOW", "DEGRADED", "HALT", "LOGFULLHALT", or "BYPASS_MODE".

        Args:
            primary_val: c0_threshold (coherence threshold)
            secondary_val: ai_confidence (the confidence score to validate)
        """
        try:
            if self._uds_available():
                return self._validate_uds(primary_val, secondary_val)
            return self._validate_tcp(primary_val, secondary_val)
        except OSError:
            return BYPASS_MODE

    def _validate_uds(self, primary: float, secondary: float) -> str:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(UDS_PATH)
            return self._exchange(s, primary, secondary)

    def _validate_tcp(self, primary: float, secondary: float) -> str:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.connect((self.tcp_host, self.tcp_port))
            return self._exchange(s, primary, secondary)

    def _exchange(self, sock: socket.socket, primary: float, secondary: float) -> str:
        """Send 18-byte InferenceTelemetryPacket to L1, receive decision.

        Maps:
            primary → c0_threshold_scaled
            secondary → ai_confidence_scaled
        """
        # Scale to micro-units for fixed-point wire format
        c0_scaled = int(primary * _TELEMETRY_SCALE)
        conf_scaled = int(secondary * _TELEMETRY_SCALE)

        # Pack 18-byte InferenceTelemetryPacket (big-endian)
        frame = struct.pack(_TELEMETRY_FMT, conf_scaled, c0_scaled, 1, 1)

        sock.sendall(frame)

        # Receive 4-byte response (Decision enum)
        resp = bytearray()
        while len(resp) < 4:
            chunk = sock.recv(4 - len(resp))
            if not chunk:
                break
            resp.extend(chunk)

        codes = {0: "ALLOW", 1: "DEGRADED", 2: "HALT", 3: "LOGFULLHALT"}
        return codes.get(resp[0], "HALT") if resp else BYPASS_MODE
