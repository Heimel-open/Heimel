# Build Order: LastSeen Query Surface

Status: IMPLEMENTED — READY TO MERGE
Owner: VALO Edge
Repository: `nsolland/valo-edge`
Canonical base: `9a14d8c38315d0ed36a06f2ccadab49ba2b61c5`
Dependency: merged governed camera privacy alpha

## Outcome

Deliver a local-only query surface over governed LastSeen memory: a standard-library HTTP API and a dependency-free web UI that bind to localhost, enforce query scope before results reach the reader, and never leave the device or call out.

## Delivered

- `lastseen-api` console script serving a local HTTP API and web UI
- `POST /observations` — store one governed observation
- `GET /objects/{name}/last-seen` — newest authorized match with camera, zone and time scope
- `GET /objects/{name}/history` — newest-first authorized history within a temporal scope
- `DELETE /objects/{name}` — remove source history and derived indexes, keeping only a deletion receipt
- `GET /receipts/{digest}` — Veritas deletion receipt or observation source receipt lookup
- single-file vanilla web UI at `/` (`src/valo_edge/lastseen/web/index.html`)
- scope enforcement in SQL before evidence is returned; results are authorization-gated by micro-REHT `READ_LAST_SEEN` / `STORE_OBSERVATION` / `DELETE_OBJECT_HISTORY`
- binds to `127.0.0.1` by default, no telemetry, no new dependencies (stdlib `http.server` only)
- SQLite connection shared from the single-threaded server thread (`check_same_thread=False`)

## Verification

- `tests/test_api.py` covers the full round trip: remember, find by alias, scoped-out 404, delete-with-receipt, receipt lookups (deletion and observation), unknown-receipt 404, missing-field 400, and web UI serving
- full suite: 34 tests passed on Python 3.12
- live smoke: `lastseen-api --db /tmp/lastseen.db` served the UI, stored via `POST /observations`, found via alias URL, returned 404 for scoped-out and unknown-receipt requests, and deleted with a receipt

## Owned files

- `src/valo_edge/lastseen/api.py`
- `src/valo_edge/lastseen/web/index.html`
- `tests/test_api.py`
- `src/valo_edge/lastseen/service.py` (`get_receipt`)
- `pyproject.toml` (`lastseen-api` script, package data)
- `README.md`
- `docs/lastseen/BUILD_ORDER_QUERY_SURFACE.md`

## Explicit non-goals

- no remote or cloud service
- no telemetry, analytics or network egress
- no authentication/authorization beyond the existing local micro-REHT envelope (single local user)
- no dense retrieval or entity graph
- no TLS (localhost only)
