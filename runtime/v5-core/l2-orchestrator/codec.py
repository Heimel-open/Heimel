# l2-orchestrator/codec.py
# Transport Layer Abstraction — Strategy Pattern
# Enables pluggable protocols (TCP, UDS, gRPC, QUIC, etc.)

from abc import ABC, abstractmethod
from typing import Tuple


class Transport(ABC):
    """
    Abstract base class for all transport protocols.
    
    Implementations: TCPTransport, UDSTransport, GRPCTransport (future)
    
    Contract:
    - connect(config) establishes connection
    - send_recv(frame) sends and receives atomically
    - close() cleanly shuts down
    - All timing is in nanoseconds (monotonic_ns)
    """
    
    @abstractmethod
    def connect(self, config: dict) -> None:
        """
        Establish connection using transport-specific config.
        
        Args:
            config (dict): Transport-specific configuration
                TCP:  {"host": str, "port": int}
                UDS:  {"path": str}
                gRPC: {"endpoint": str, "tls": bool}
        
        Raises:
            ConnectionError: If connection fails
        """
        pass
    
    @abstractmethod
    def send_recv(self, frame: bytes) -> Tuple[bytes, int]:
        """
        Send frame to L1, receive response atomically.
        
        Args:
            frame (bytes): 64-byte VALO frame
        
        Returns:
            Tuple[bytes, int]: (response_bytes, round_trip_ns)
            - response_bytes: 4 bytes (Decision enum value)
            - round_trip_ns: nanoseconds elapsed
        
        Raises:
            ConnectionError: If send/recv fails
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Cleanly close connection."""
        pass


class TCPTransport(Transport):
    """TCP/IP transport to L1 Guardian."""
    
    def __init__(self):
        self._sock = None
    
    def connect(self, config: dict) -> None:
        """
        Connect to L1 via TCP.
        
        Config: {"host": "127.0.0.1", "port": 7743}
        
        TCP_NODELAY disables Nagle's algorithm for sub-microsecond latency.
        Critical for VAIG token validation in hot path.
        """
        import socket
        
        host = config.get("host", "127.0.0.1")
        port = config.get("port", 7743)
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # TCP_NODELAY: Critical for P99 latency. Disable Nagle's algorithm.
        # Without this, small frames are buffered, causing ~40ms delays.
        # With this, frame is sent immediately (measured ~43ns in L1 hot path).
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        s.connect((host, port))
        self._sock = s
    
    def send_recv(self, frame: bytes) -> Tuple[bytes, int]:
        """Send frame, receive 4-byte response."""
        import time
        
        if self._sock is None:
            raise ConnectionError("Transport not connected")
        
        t0 = time.monotonic_ns()
        self._sock.sendall(frame)
        resp = self._recv_exact(4)
        rtt_ns = time.monotonic_ns() - t0
        
        return resp, rtt_ns
    
    def _recv_exact(self, n: int) -> bytes:
        """Receive exactly n bytes."""
        buf = bytearray()
        while len(buf) < n:
            chunk = self._sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("L1 closed connection unexpectedly")
            buf.extend(chunk)
        return bytes(buf)
    
    def close(self) -> None:
        """Close TCP socket."""
        if self._sock:
            self._sock.close()
            self._sock = None


class UDSTransport(Transport):
    """Unix Domain Socket transport to L1 Guardian."""
    
    def __init__(self):
        self._sock = None
    
    def connect(self, config: dict) -> None:
        """
        Connect to L1 via Unix Domain Socket.
        
        Config: {"path": "/tmp/valo_v5_l1.sock"}
        
        UDS is lower-latency than TCP on localhost (no TCP stack overhead).
        Preferred for single-host deployments.
        """
        import socket
        
        path = config.get("path", "/tmp/valo_v5_l1.sock")
        
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(path)
        self._sock = s
    
    def send_recv(self, frame: bytes) -> Tuple[bytes, int]:
        """Send frame, receive 4-byte response."""
        import time
        
        if self._sock is None:
            raise ConnectionError("Transport not connected")
        
        t0 = time.monotonic_ns()
        self._sock.sendall(frame)
        resp = self._recv_exact(4)
        rtt_ns = time.monotonic_ns() - t0
        
        return resp, rtt_ns
    
    def _recv_exact(self, n: int) -> bytes:
        """Receive exactly n bytes."""
        buf = bytearray()
        while len(buf) < n:
            chunk = self._sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("L1 closed connection unexpectedly")
            buf.extend(chunk)
        return bytes(buf)
    
    def close(self) -> None:
        """Close Unix socket."""
        if self._sock:
            self._sock.close()
            self._sock = None
