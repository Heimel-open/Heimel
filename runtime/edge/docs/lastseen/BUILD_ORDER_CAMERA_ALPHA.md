# Build Order: LastSeen Camera Alpha

Status: VERIFIED — READY TO MERGE
Owner: ChatGPT implementation worker
Independent verification: GitHub Actions
Repository: `nsolland/valo-edge`
Canonical base: `63317ffc57471b6ea962315a543cde58face016b`
Branch: `feat/lastseen-camera-alpha`
PR: `#6`
Dependency: merged temporal local memory and `ADR_ZERO_TOKEN_EDGE_MEMORY.md`

## Delivered

- detector-neutral camera and bounding-box contracts
- deterministic local replay adapter
- YAML camera-zone to human-location mapping
- atomic local PNG crop store with existing-artifact integrity verification
- crop persistence only after micro-REHT clearance
- person detections excluded from memory
- any object crop intersecting a detected person rejected fail-closed
- configurable minimum confidence and unknown-zone rejection
- deterministic camera source IDs linked to frame, detector and bounding box
- LastSeen provenance linking crop receipt, frame digest, detector, camera and zone
- compensating governed crop deletion when memory storage fails
- pipeline-owned raw frame buffer zeroized in `finally`, including detector failure paths
- local camera CLI and reproducible replay fixture

## Verification

GitHub Actions run `30911122028`:

- Python 3.10: tests, LastSeen memory smoke and camera replay smoke passed
- Python 3.11: tests, LastSeen memory smoke and camera replay smoke passed
- Python 3.12: tests, LastSeen memory smoke and camera replay smoke passed

Focused camera tests cover:

- safe crop persistence and provenance
- person exclusion and overlap rejection
- unknown-zone and confidence fail-closed paths
- duplicate replay without deleting the original crop
- invalid person boundary with mandatory raw-buffer disposal
- detector failure with mandatory raw-buffer disposal

## Owned files

- `src/valo_edge/lastseen/camera.py`
- `src/valo_edge/lastseen/camera_cli.py`
- `tests/test_lastseen_camera.py`
- `examples/lastseen-camera/**`
- `pyproject.toml`
- `.github/workflows/lastseen-ci.yml`
- `README.md`
- `docs/lastseen/BUILD_ORDER_CAMERA_ALPHA.md`

## Explicit non-goals

- live ONNX model execution
- Raspberry Pi camera driver
- face recognition or person tracking
- remote API or cloud service
- dense retrieval or entity graph
