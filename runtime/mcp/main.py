#!/usr/bin/env python3
"""VALO MCP Gateway — entrypoint."""
import os
import sys
import logging
from pathlib import Path

# Ensure package imports work when run from repo root
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

from broker.broker import ValoBroker
from server.server import create_mcp_server

LOG_LEVEL = os.getenv("VAIG_LOG_LEVEL", "INFO").upper()
DB_PATH = os.getenv("VAIG_DB_PATH", str(REPO / "var" / "valo.db"))

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("valo.mcp")

def main() -> int:
    log.info("Starting VALO MCP Gateway")
    log.info("DB path: %s", DB_PATH)

    broker = ValoBroker(db_path=DB_PATH)
    mcp = create_mcp_server(broker)

    log.info("MCP server ready — awaiting agent connections")
    mcp.run()
    return 0

if __name__ == "__main__":
    sys.exit(main())
