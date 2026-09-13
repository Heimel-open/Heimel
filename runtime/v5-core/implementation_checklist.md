# VALO V5.0 Implementation Checklist

## Fase 1: Truth-in-Repo (DONE ✅)
- [x] Create docs/ARCHITECTURE.md
- [x] Create .github/copilot-instructions.md
- [x] Create tests/fixtures/test_vectors.json (with version 5.0.0)
- [x] Update .github/workflows/verify.yml (validate schema, observability check)

## Fase 2: Transport Strategy Implementation (DONE ✅)

### Step 1: Create l2-orchestrator/codec.py
- [x] Define Transport ABC (abstract base class)
- [x] Implement TCPTransport
- [x] Implement UDSTransport

### Step 2: Create l2-orchestrator/observability.py
- [x] Define LogLevel enum
- [x] Implement emit_log() for structured JSON
- [x] Implement log_halt() with full audit context
- [x] Implement log_decision() for every frame

### Step 3: Refactor l2-orchestrator/bridge.py
- [x] Update ValoBridge.__init__ to accept Transport
- [x] Update connect() to use transport.connect(config)
- [x] Add connect_uds(path) convenience wrapper
- [x] Update send_frame() to call log_decision() and log_halt()
- [x] Add pack_valo_frame() compatibility wrapper (val_secondary→ai_confidence, val_primary→c0_threshold)
- [x] Create BridgeFactory in l2-orchestrator/__init__.py

### Step 4: Update entry points
- [x] sidecar/vaig.py — uses BridgeFactory + Transport
- [x] demo-server/app.py — uses BridgeFactory + Transport
- [x] mcp_server.py — MCP ingress now includes `process_permit` on the golden path, alongside legacy telemetry tools

## Fase 3: Code Quality + Consistency (DONE ✅)

### bridge.py cleanup
- [x] Remove pack_telemetry_packet reimplementation confusion — kept as primary, pack_valo_frame is wrapper
- [x] Propagator.py — replaced importlib hack with BridgeFactory bootstrap
- [x] janus_integration.py — replaced importlib hack with BridgeFactory; added StructuredLogger

### simulate.py consolidation
- [x] Merged simulate.py + simulate_vaig.py → single simulate.py --mode infra|vaig|all
- [x] simulate_vaig.py kept as backward-compat shim

### TLA+ cleanup
- [x] Remove NoIllegalHalt from valo_v5.tla (duplicate of SafetyInvariant)
- [x] valo_v5.cfg: Add TypeInvariant + SafetyInvariant as INVARIANTS; remove NoIllegalHalt
- [x] valo_v5.tla: Add MaxDegradedTime CONSTANT, replace hardcoded 30
- [x] ValoStateMachine.tla: Remove dead ELSE branch in context_age increment

### Dead code removal
- [x] Delete l2-orchestrator/ai_gateway.py (stub, never imported)
- [x] Delete l2-orchestrator/weather_api_v1.py (wrong layer, privacy leak)
- [x] Delete l3-context/src/feeds.rs (empty stub, never integrated)
- [x] Remove crc32c::verify() (dead function)

### Minor fixes
- [x] observability.py: datetime.utcnow() → datetime.now(timezone.utc)
- [x] sidecar/vaig.py: StructuredLogger.set_component("vaig")
- [x] demo-server/app.py: StructuredLogger.set_component("demo-server")
- [x] janus_integration.py: StructuredLogger.set_component("janus-gateway")

## Fase 4: Distroless Docker + Observability (PENDING)

### Dockerfile
- [ ] Update Stage 1 (rust-builder) — unchanged
- [ ] Update Stage 2 (deps) — unchanged
- [ ] Add Stage 3 (distroless) — FROM gcr.io/distroless/python3-debian12:nonroot
- [ ] Set ENV VALO_LOG_ENDPOINT="stdout"
- [ ] Test locally with docker build + docker run

---

## Fase 5: Test Vector JSON Integration (PENDING)

### demo-server/app.py
- [ ] Replace INFRA_TESTS/VAIG_TESTS hardcoded tuples with JSON loader from tests/fixtures/test_vectors.json
- [ ] Add version check: assert fixtures['version'] == '5.0.0'

---

## Pre-Merge Checklist

Before merging to main:

- [x] All entry points use BridgeFactory (no raw importlib hacks)
- [x] pack_valo_frame() defined — all callers unblocked
- [x] TLA+ specs clean (no vacuous/duplicate properties)
- [x] mcp_server.py implemented with legacy telemetry tools plus `process_permit` golden-path ingress
- [ ] Test vectors loaded from JSON in demo-server
- [x] No socket hardcoding in vaig.py / demo-server
- [x] HALT events logged via observability module
- [x] Version field in test_vectors.json matches docs

---

## Architecture Decision: L3 Layer

The Rust `l3-context/` module (context_engine.rs, distrust.rs, main.rs) is a stub layer.
The real L3 is VAIG (Python), accessed via `sidecar/vaig.py`.
Recommendation: retire Rust L3 stubs in a future cleanup pass; do not add new code there.
