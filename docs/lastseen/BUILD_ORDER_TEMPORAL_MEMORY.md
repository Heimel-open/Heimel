# Build Order: LastSeen Temporal Local Memory

Status: VERIFIED — READY TO MERGE
Owner: ChatGPT implementation worker
Independent verification: GitHub CI
Repository: `nsolland/valo-edge`
Canonical base: `4a4dd0dcd875c15c77dc0a1f3b846c9fdd906291`
Branch: `feat/lastseen-temporal-memory`
PR: `#5` — ready for review
Dependency: merged LastSeen MVP and `ADR_ZERO_TOKEN_EDGE_MEMORY.md`

## Delivered

- immutable source identifiers and preserved source receipts
- observation and ingestion timestamps
- source type, source device, camera, zone and policy provenance
- deterministic day, hour and episode indexing
- persisted aliases as rebuildable derived index entries
- authorized latest and history reads scoped by camera, zone and time
- explicit governed `REBUILD_MEMORY_INDEX`
- deterministic index manifest digest
- legacy SQLite migration without source-evidence loss
- cascading removal of derived index entries during deletion
- salted, non-recoverable deletion subject digest and Veritas receipt
- CLI support for provenance, history, scope, index rebuild and deletion receipts

## Verification

Local isolated execution against the repository's current contracts, micro-REHT and gateway implementations:

- 8/8 focused tests passed
- CLI demo passed
- scoped history CLI passed
- remote Git blob SHAs matched the locally executed source, CLI, exports and tests

Independent GitHub Actions run `30908013243`:

- Python 3.10: test and LastSeen smoke demo passed
- Python 3.11: test and LastSeen smoke demo passed
- Python 3.12: test and LastSeen smoke demo passed

## Owned files

- `src/valo_edge/lastseen/service.py`
- `src/valo_edge/lastseen/cli.py`
- `src/valo_edge/lastseen/__init__.py`
- `tests/test_lastseen.py`
- `docs/lastseen/BUILD_ORDER_TEMPORAL_MEMORY.md`

## Explicit non-goals

- camera drivers
- dense retrieval
- entity graph
- remote API or cloud service
- generative memory construction
