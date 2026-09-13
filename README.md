# VALO Edge

VALO Edge is the embeddable authorization and evidence layer for local and physical AI. Models and sensors may interpret and propose. micro-REHT decides whether an exact consequence is authorized now. The device gateway mechanically enforces the exact authorized command. Veritas Edge records verifiable evidence of what was authorized, enforced and observed.

## LastSeen

**Your home remembers. The cloud doesn't.**

LastSeen is the first open-source VALO Edge product demo: private, local visual memory for everyday objects. Ask where your keys, glasses, wallet or remote were last seen. Object observations remain local, and storing, reading or deleting memory is governed at the moment of consequence.

The local product provides:

- governed SQLite object memory with source provenance
- deterministic temporal and alias retrieval
- explicit deletion and index rebuilding
- local detector replay and zone mapping
- object crops persisted only after micro-REHT clearance
- person detections and person-overlapping crops rejected fail-closed
- raw camera frames zeroized in memory after every processing attempt
- Veritas receipts for memory, crop and disposal consequences
- no network dependency

### Run the memory demo

```bash
python -m pip install -e ".[dev]"
lastseen --db /tmp/lastseen.db demo
```

Record and find an object:

```bash
lastseen remember keys "kitchen counter, beside the coffee machine" \
  --image crops/keys-kitchen.jpg --confidence 0.98

lastseen find keys --alias nøkler
```

### Run the camera replay alpha

```bash
python -m pip install -e ".[camera]"
lastseen-camera \
  --db /tmp/lastseen-camera.db \
  --crop-dir /tmp/lastseen-crops \
  --zones examples/lastseen-camera/zones.yaml \
  replay examples/lastseen-camera/replay.json
```

The included replay stores the safe keys crop, excludes the person detection, rejects the wallet crop because it intersects the detected person, and emits a verified raw-frame disposal receipt.

### Run the local web UI and HTTP API

```bash
python -m pip install -e ".[dev]"
lastseen-api --db /tmp/lastseen.db
```

Then open `http://127.0.0.1:8080/`. The server binds to localhost only and has no telemetry. The API surface:

- `POST /observations` — store one governed observation
- `GET /objects/{name}/last-seen` — newest authorized match (scope via `camera_id`, `zone_id`, `since`, `until`, `alias`)
- `GET /objects/{name}/history` — newest-first authorized history within a temporal scope
- `DELETE /objects/{name}` — remove source history and derived indexes, keeping only a deletion receipt
- `GET /receipts/{digest}` — Veritas deletion receipt or observation source receipt

### Build orders and decisions

- [`docs/lastseen/BUILD_ORDER_MVP.md`](docs/lastseen/BUILD_ORDER_MVP.md)
- [`docs/lastseen/BUILD_ORDER_TEMPORAL_MEMORY.md`](docs/lastseen/BUILD_ORDER_TEMPORAL_MEMORY.md)
- [`docs/lastseen/BUILD_ORDER_CAMERA_ALPHA.md`](docs/lastseen/BUILD_ORDER_CAMERA_ALPHA.md)
- [`docs/lastseen/BUILD_ORDER_QUERY_SURFACE.md`](docs/lastseen/BUILD_ORDER_QUERY_SURFACE.md)
- [`docs/lastseen/BUILD_ORDER_NEXT.md`](docs/lastseen/BUILD_ORDER_NEXT.md)
- [`docs/edge/BUILD_ORDER_VAIG_V1.md`](docs/edge/BUILD_ORDER_VAIG_V1.md)
- [`docs/edge/BUILD_ORDER_MICRO_REHT_V1.md`](docs/edge/BUILD_ORDER_MICRO_REHT_V1.md)
- [`docs/edge/BUILD_ORDER_DEVICE_GATEWAY_V1.md`](docs/edge/BUILD_ORDER_DEVICE_GATEWAY_V1.md)
- [`docs/edge/BUILD_ORDER_VERITAS_EDGE_V1.md`](docs/edge/BUILD_ORDER_VERITAS_EDGE_V1.md)
- [`docs/lastseen/ADR_ZERO_TOKEN_EDGE_MEMORY.md`](docs/lastseen/ADR_ZERO_TOKEN_EDGE_MEMORY.md)

### Memory doctrine

Original local observations and Veritas receipts are the source of record. Aliases, lexical indexes, temporal hierarchies, embeddings and entity graphs are derived retrieval structures only. They must resolve back to source observations and must not rewrite history.

Memory operations should remain local and non-generative: no LLM is required to ingest, index, route, retrieve, calibrate or delete memory. A model may interpret retrieved evidence, but micro-REHT decides whether the concrete memory consequence is allowed.

## Product Track & Identity

- **Product Track**: VALO Edge
- **Constrained Profile**: Tiny Edge
- **Current package**: `v0.3.0`
- **Core Principles**:
  - Deterministic serialization and SHA-256 evidence hashing
  - No direct model-to-actuator or model-to-storage path
  - Monotonic decision preservation: HALT, DENY and DEFER cannot be upgraded downstream
  - Mutation and replay rejection
  - Offline authority envelope limits
  - Fail-closed evaluation on missing or invalid identity, policy or firmware
  - Deterministic emulator and test suite

## Architecture

```text
local detector / sensor
        |
        v
structured proposal
        |
        v
Local VAIG evidence
        |
        v
micro-REHT clearance
        |
        v
Device Enforcement Gateway
        |
        v
device driver / bounded actuator
        |
        v
Veritas Edge evidence chain
```

The gateway is mechanical enforcement only. It does not evaluate evidence, create authority, reinterpret policy or upgrade a micro-REHT outcome.

Veritas Edge is evidence only. It records the authorization receipt, the gateway enforcement receipt and the post-driver observation in an append-only chain. It preserves the difference between a driver-reported execution, a gateway rejection before any driver call, and an uncertain timeout. A driver report is not silently promoted to physical truth; independent physical observation may be bound by digest when available.

```text
src/valo_edge/
├── contracts/               # Versioned consequence contracts
├── vaig/                    # Local evidence evaluation; never authority
├── runtime/                 # Deterministic micro-REHT authorization
├── gateway/                 # Mechanical exact-command enforcement
├── veritas/                 # Append-only consequence evidence and export
├── governance/              # Embedded governance primitives (stdlib-only, on-device)
│   ├── canonical.py         # RFC 8785-subset canonical SHA-256 digest
│   ├── worm.py              # Append-only hash-chained audit log
│   ├── revocation.py        # M-of-N guardian revocation with hash chain
│   └── ratelimit.py         # Sliding-window rate limiter
├── device/                  # Embedded device governance composition
├── adapters/                # Replaceable sensor and model runtime adapters
├── tinyllm/                 # Constrained local model and camera intake
└── lastseen/                # Governed local object and camera memory
```

## Initial Edge Features

- Edge action commitment contract
- Local VAIG Edge evidence profile
- Device, firmware, runtime and model evidence binding
- Sensor provenance, freshness and physical-state consistency
- Explicit missing, stale, contradictory and untrusted evidence
- Model-free evidence path when no model participates
- Signed offline authority envelopes
- Exact action, parameter and physical-state authorization
- Use, rate, energy, duration and value budgets
- Restart-safe replay, mutation and monotonic sequence protection
- Persistent HALT and bounded consumable permits
- Edge clearance contract
- micro-REHT emulator and V1 authorization runtime
- Device Enforcement Gateway V1 with exact proposal/clearance/command binding
- One-use permit enforcement and duplicate command rejection
- Actual driver outcomes: executed, partial, failed and timeout
- Edge enforcement contract for downstream Veritas observation
- Veritas Edge authorization, enforcement and execution-observation receipts
- Durable append-only JSONL evidence chain with boot-epoch continuity
- Explicit driver-reported, gateway-rejected and timeout-unknown evidence states
- Failure, partial and compensation evidence records
- Self-verifiable evidence packages with reference HMAC attestation and reconciliation receipts
- Hardware-neutral gateway emulator retained for legacy demos
- Embedded governance primitives: canonical digest, WORM audit log, M-of-N revocation and sliding-window rate limit
- TinyLLM sensor and camera intake
- LastSeen temporal local memory
- LastSeen governed camera replay alpha
- LastSeen local HTTP API and web UI
- Sensor-to-safe-actuator demonstration
- Mismatch, expiry, mutation, replay, rate-limit, HALT and reconnect tests
- Persistent anti-replay state across restarts and gateway evidence chaining

## License

MIT
