# l2-orchestrator/observability.py
# Structured Logging for VALO V5.0
# All output to stdout (JSON) for container aggregation (CloudWatch, ELK, Datadog)

import json
import sys
from datetime import datetime, timezone
from enum import Enum
from threading import Lock


class LogLevel(Enum):
    """Structured log levels."""
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    HALT = "HALT"  # Critical level for Decision.HALT events


class StructuredLogger:
    """
    Emits structured JSON logs to stdout.
    
    Thread-safe for async/multi-threaded contexts (asyncio, threading).
    
    In Distroless containers:
    - No /bin/bash, no local file access
    - All debugging via structured logs
    - stdout automatically captured by container aggregator
    
    Compatible with:
    - CloudWatch Logs (via ECS, parses JSON automatically)
    - ELK Stack (Elasticsearch → Logstash → Kibana)
    - Datadog (native JSON integration, extracts fields)
    
    JSON Schema (consistent for all messages):
    {
        "timestamp": "2026-06-07T12:34:56.789Z",
        "level": "INFO|WARN|ERROR|HALT",
        "component": "valo-bridge",
        "message": "Human-readable message",
        "context": { ... }
    }
    
    This schema allows jq parsing:
        jq 'select(.level=="HALT")' valo-logs.jsonl
    """
    
    _lock = Lock()  # Thread-safe stdout writes
    _component = "valo-bridge"  # Default component name
    
    @classmethod
    def set_component(cls, component: str) -> None:
        """Set component name for all subsequent logs (e.g., 'vaig', 'mcp-server')."""
        cls._component = component
    
    @staticmethod
    def emit(level: LogLevel, message: str, context: dict = None) -> None:
        """
        Emit structured JSON log entry to stdout.
        
        Thread-safe via lock. All writes are atomic.
        
        Args:
            level (LogLevel): Log level (INFO, WARN, ERROR, HALT)
            message (str): Human-readable message
            context (dict): Contextual data (flattened into JSON)
        """
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.value,
            "component": StructuredLogger._component,
            "message": message,
            "context": context or {},
        }
        
        # Thread-safe print to stdout
        with StructuredLogger._lock:
            print(json.dumps(log_entry, default=str), file=sys.stdout, flush=True)
    
    @staticmethod
    def log_info(message: str, **context) -> None:
        """Log informational event."""
        StructuredLogger.emit(LogLevel.INFO, message, context)
    
    @staticmethod
    def log_warn(message: str, **context) -> None:
        """Log warning event."""
        StructuredLogger.emit(LogLevel.WARN, message, context)
    
    @staticmethod
    def log_error(message: str, **context) -> None:
        """Log error event."""
        StructuredLogger.emit(LogLevel.ERROR, message, context)
    
    @staticmethod
    def log_halt(frame_id: int, val_primary: float, val_secondary: float,
                 max_spread: float, reason: str, distrust_level: int) -> None:
        """
        Log a HALT decision with full audit context.
        
        JSON format for compliance audit (EU AI Act Article 12):
        {
            "timestamp": "...",
            "level": "HALT",
            "component": "...",
            "message": "L1 Guardian HALT: CRC32C_MISMATCH",
            "context": {
                "frame_id": 12345,
                "val_primary": 0.95,
                "val_secondary": 0.30,
                "max_spread": 5.0,
                "reason": "CRC32C_MISMATCH",
                "distrust_level": 0
            }
        }
        
        Args:
            frame_id (int): Frame identifier
            val_primary (float): Primary value from frame
            val_secondary (float): Secondary value from frame
            max_spread (float): Max spread tolerance from frame
            reason (str): Why HALT was triggered (e.g., "CRC32C_MISMATCH", "F1_NEGATIVE_SPREAD", "F2A_SPREAD_OVERFLOW")
            distrust_level (int): L3 distrust level (0-4) at time of HALT
        """
        StructuredLogger.emit(
            LogLevel.HALT,
            f"L1 Guardian HALT: {reason}",
            context={
                "frame_id": frame_id,
                "val_primary": val_primary,
                "val_secondary": val_secondary,
                "max_spread": max_spread,
                "reason": reason,
                "distrust_level": distrust_level,
            }
        )
    
    @staticmethod
    def log_decision(decision: str, frame_id: int, rtt_us: float,
                     distrust_level: int = 0) -> None:
        """
        Log every decision for audit trail.
        
        JSON format for decision audit:
        {
            "timestamp": "...",
            "level": "INFO",
            "component": "...",
            "message": "Decision: ALLOW",
            "context": {
                "frame_id": 12345,
                "decision": "ALLOW",
                "rtt_microseconds": 43.21,
                "distrust_level": 0
            }
        }
        
        Args:
            decision (str): Decision name (ALLOW, DEGRADED, HALT, LOGFULLHALT)
            frame_id (int): Frame identifier
            rtt_us (float): Round-trip time in microseconds
            distrust_level (int): Current distrust level (optional)
        """
        StructuredLogger.emit(
            LogLevel.INFO,
            f"Decision: {decision}",
            context={
                "frame_id": frame_id,
                "decision": decision,
                "rtt_microseconds": round(rtt_us, 2),
                "distrust_level": distrust_level,
            }
        )


# Convenience module-level functions for backward compatibility
def log_info(message: str, **context) -> None:
    """Log informational event."""
    StructuredLogger.log_info(message, **context)


def log_warn(message: str, **context) -> None:
    """Log warning event."""
    StructuredLogger.log_warn(message, **context)


def log_error(message: str, **context) -> None:
    """Log error event."""
    StructuredLogger.log_error(message, **context)


def log_halt(frame_id: int, val_primary: float, val_secondary: float,
             max_spread: float, reason: str, distrust_level: int) -> None:
    """Log a HALT decision with full audit context."""
    StructuredLogger.log_halt(frame_id, val_primary, val_secondary,
                              max_spread, reason, distrust_level)


def log_decision(decision: str, frame_id: int, rtt_us: float,
                 distrust_level: int = 0) -> None:
    """Log every decision for audit trail."""
    StructuredLogger.log_decision(decision, frame_id, rtt_us, distrust_level)
