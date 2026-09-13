# VALO MCP Gateway
Sidecar governance-core exposing VAIG/RACS via Model Context Protocol.

## Structure
- `main.py` — startup entrypoint
- `broker/broker.py` — governance core (evidence, clearance, receipts)
- `server/server.py` — MCP server exposing tools to AI agents

## Run
```bash
python main.py
```

## Config
Set env vars:
- `VAIG_DB_PATH` — path to receipts DB (default: ./var/valo.db)
- `VAIG_LOG_LEVEL` — INFO/DEBUG (default: INFO)
