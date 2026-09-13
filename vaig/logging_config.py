"""Structured logging for VAIG.

Replaces all print() statements with proper Python logging.
JSON output for production, human-readable for development.

Usage:
    from vaig.logging_config import setup_logging, get_logger
    setup_logging(level="INFO", json_output=True)
    logger = get_logger("vaig.ensemble")
    logger.info("evaluating", extra={"prompt_hash": "abc123", "response_len": 500})
"""

from __future__ import annotations

import logging
import sys
import json
from datetime import datetime, timezone
from typing import Optional


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Include extra fields
        for key in ("prompt_hash", "response_len", "instrument", "score", 
                    "level_name", "latency_ms", "entry_id", "worm_hash",
                    "distrust_level", "error", "config_key"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)

        # Include exception info
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class HumanFormatter(logging.Formatter):
    """Human-readable formatter for development."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        location = f"{record.module}:{record.lineno}"
        return f"[{timestamp}] {record.levelname:8s} {record.name:20s} {location:20s} {record.getMessage()}"


def setup_logging(
    level: str = "INFO",
    json_output: bool = True,
    logger_name: str = "vaig",
) -> logging.Logger:
    """Configure VAIG logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: True for JSON logs, False for human-readable
        logger_name: Root logger name (default: "vaig")

    Returns:
        Configured root logger
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, level.upper()))

    # Clear existing handlers
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))

    if json_output:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(HumanFormatter())

    logger.addHandler(handler)

    # Prevent propagation to root logger (avoid double logging)
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a VAIG sub-logger. Names should be dot-separated.

    Examples:
        get_logger("vaig.ensemble")
        get_logger("vaig.worm")
        get_logger("vaig.instruments.registry")
    """
    return logging.getLogger(name)
