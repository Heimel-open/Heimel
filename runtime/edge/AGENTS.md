# AGENTS.md

## What this is

VALO Edge is the embeddable authorization and evidence layer for local and physical AI. Models and sensors may interpret and propose; **micro-REHT** decides whether an exact consequence is authorized now; a **hardware-neutral gateway** enforces the decision; **Veritas** receipts prove what happened.

The first open-source product is **LastSeen**: governed, privacy-preserving local visual memory (`valo_edge.lastseen`).

## Non-negotiable invariants

- **No direct model-to-actuator or model-to-storage path.** Every consequence goes through `MicroRehtEngine.evaluate_proposal` → `HardwareNeutralGateway.execute_action`.
- **Fail closed** on missing/invalid identity, policy, firmware, envelope revocation/expiry, replay (nonce reuse), rate-limit breach or proposal hash mismatch. Person detections are never persisted as object memories.
- **Rate limits are real.** `OfflineAuthorityEnvelope.max_rate_per_sec` is enforced per envelope in `MicroRehtEngine`; do not treat it as metadata.
- **Anti-replay survives restart.** `MicroRehtEngine` persists `seen_nonces` to a state file (`<db>.replay-state.json`) loaded at construction and flushed on `LastSeenService.close`. Never disable this path.
- **Determinism.** All digests are SHA-256 over canonical payloads: `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False)`. Use `_stable_hash`/`_digest` helpers; never a non-canonical or non-sorted payload.
- **Monotonic decisions.** HALT, DENY and DEFER cannot be upgraded downstream.
- **Evidence chaining.** `HardwareNeutralGateway.execute_action` recomputes and rejects on clearance `decision_digest` mismatch, `proposal_id` mismatch or proposal hash mismatch. Never accept a clearance without its verified digest.
- **Provenance doctrine** (`docs/lastseen/ADR_ZERO_TOKEN_EDGE_MEMORY.md`): original observations and receipts are the source of record. Aliases, lexical indexes and temporal structures are derived and must resolve back to source `source_id`s; they never rewrite history. Derived indexes must be rebuildable deterministically from retained sources (`rebuild_indexes`).
- **Perception adapters are not authority** (`docs/edge/ADR_PERCEPTION_ADAPTER_LINEAGE.md`). Voice isolation, denoising, enhancement and equivalent transforms are replaceable preprocessing components. Preserve attributable lineage from original observation through adapter/model/version, transformed observation and downstream interpretation to evidence, decision, action and receipt; never silently substitute transformed evidence for the source observation.
- **Deletion** removes source content and all derived index references, retaining only a non-reversible receipt (digest, policy version, timestamp, count). Never retain recoverable personal content in a deletion receipt.
- **Privacy**: raw camera frames live in memory only and are zeroized after every processing attempt (`CameraFrame.zeroize`). Only object crops are persisted, and only after micro-REHT clearance (`PERSIST_OBJECT_CROP`).
- **No LLM or network dependency** is required for memory ingest, index, retrieve, calibrate or delete.
- **Timestamps** are canonical ISO-8601 UTC with `Z` (see `_canonical_iso` / `_utc_now_iso`).

## Layout

```
src/valo_edge/
├── contracts/    # Edge action, clearance, receipt contracts (pydantic, SHA-256 digests)
├── runtime/      # Deterministic fail-closed micro-REHT engine
├── gateway/      # Hardware-neutral enforcement gateway + Veritas receipts
├── tinyllm/      # Constrained local model + physical operator/camera intake
├── adapters/     # Sensor/operator → EdgeActionProposal adapters
├── lastseen/     # Governed local object + camera memory (service, camera pipeline, API, web UI, CLIs)
└── demos/        # Demo scripts
docs/lastseen/    # Build orders and ADRs — read before extending
examples/         # Replay fixtures, zone YAML
```

## Conventions

- Python `>=3.10`, style compatible with 3.10 (avoid 3.12-only syntax unless verified in CI matrix).
- Contracts: `pydantic.BaseModel` with `compute_hash`/`compute_digest` and `model_post_init` auto-fill; `str`/`Enum` decisions from `EdgeDecision`.
- Domain objects: frozen dataclasses; validate eagerly and raise `ValueError`; use `tuple` for immutable sequences.
- `from __future__ import annotations` where union syntax is used.
- Do not add comments unless they carry intent that the code does not.
- New governed actions must be added to an `OfflineAuthorityEnvelope.allowed_action_types` list in one place and covered by tests.
- SQLite schema changes must add a `_migrate_legacy_rows`/column-migration path, never drop or rewrite existing evidence.
- The local API server is single-threaded by design; keep SQLite access serialized.

## Commands

System Python here is PEP 668-managed (`externally-managed-environment`), so use a venv or `PYTHONPATH`:

```bash
# full test suite (34 tests)
PYTHONPATH=src python3 -m pytest -q

# single area
PYTHONPATH=src python3 -m pytest -q tests/test_lastseen.py tests/test_lastseen_camera.py

# smoke tests (as in .github/workflows/lastseen-ci.yml)
lastseen --db /tmp/lastseen.db demo
lastseen-camera --db /tmp/lastseen-camera.db --crop-dir /tmp/lastseen-crops \
  --zones examples/lastseen-camera/zones.yaml replay examples/lastseen-camera/replay.json

# local HTTP API + web UI (binds to 127.0.0.1, no telemetry)
lastseen-api --db /tmp/lastseen.db --port 8080
```

In a proper environment the documented install is `python -m pip install -e ".[dev]"`; CI runs Python 3.10/3.11/3.12 on Linux.

## Testing expectations

Tests must cover: contract digest determinism, ALLOW/DENY paths, mismatch/expiry/mutation/replay/HALT, rate-limit enforcement and window reset, nonce persistence across engine restart, gateway rejection of tampered clearance digests, fail-closed invalid input, temporal and camera scope, alias/derived-index rebuild determinism, complete deletion leaving only a non-reversible receipt, legacy DB migration, raw-frame zeroization, crop rejection (person, person-overlap, below confidence, no-authorized-zone), and the local API round trip (remember, find, scoped 404, delete-with-receipt, receipt lookup, web UI).
