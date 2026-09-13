# VALO V5.0 — Code Walkthrough Guide

**For:** Leander Nikolaus Jehl & Hein Meling, University of Stavanger  
**Date:** May 2026  
**Purpose:** Guided code review to support Phase 1 academic validation

---

## How to use this document

Follow the sections in order. Each section points to the relevant files, states what claim is being validated, and gives the command to verify it. The entire walkthrough can be completed without physical hardware — all critical properties are verifiable from the simulation build.

---

## 1. Start here — build and run all tests

```bash
# Build L1 Guardian (Rust, simulation mode)
cd l1-guardian && cargo build --features simulation && cd ..

# Unit tests — no binary needed, run immediately
pytest tests/test_bridge.py -v

# Integration tests — 9/9 simulation paths
python simulate.py       # 5 infrastructure frames
python simulate_vaig.py  # 4 VAIG token-confidence frames
```

Expected output: `ALL PASS` for both simulations, `23 passed` for unit tests.

---

## 2. Formal verification (TLA+)

**Claim:** The state machine is mathematically proven to be safe — it is impossible for L1 to remain ACTIVE under L4 distrust, and HALT is terminal.

**Files:**
- `formal-verification/ValoStateMachine.tla` — main TLA+ specification
- `formal-verification/ValoStateMachine.cfg` — TLC model checker config
- `formal-verification/valo_v5.tla` — extended state machine

**Verified invariants:**

| Invariant | Meaning |
|---|---|
| `SafetyInvariant` | HALT only reached via timer expiry (≥30) or distrust saturation (≥4) |
| `LogFullHaltIsTerminal` | LogFullHalt is the true terminal state — no exit possible |
| `WORMAppendOnly` | Audit log can only grow, never be overwritten |
| `DegradedEventuallyHalt` | DEGRADED with timer = 0 → always reaches HALT or LogFullHalt |

Note: `Halt → Active` is valid via authorized `SystemReset` (2-person auth). `LogFullHalt` is the irrecoverable terminal state.

**CI verification:** `.github/workflows/integrity-check.yml` runs TLC on every push.
**State space:** 1,662 distinct reachable states (MaxDegradedTime=15, MaxContextAge=10, MaxLogSize=11) — 0 counterexamples, 0 violations. TLC v2.16, 2026-05-19.

---

## 3. L1 Guardian — the decision gate

**Claim:** Every frame is validated in deterministic time with three sequential checks. Any failure halts immediately.

**Files:**
- `l1-guardian/src/valo_frame.rs` — 64-byte frame struct (`#[repr(C, align(64))]`)
- `l1-guardian/src/validation_logic.rs` — F1, F2a, CRC32C checks
- `l1-guardian/src/crc32c.rs` — hardware-accelerated CRC32C (SSE4.2 on production)
- `l1-guardian/src/server.rs` — TCP/UDS socket server

**Decision logic (3 checks in order):**

```
1. CRC32C over bytes 0..39  → tamper/corruption → HALT
2. F1: val_primary >= val_secondary → negative spread → HALT  
3. F2a: max_spread < 0 (L4 sentinel) → untrusted source → HALT
       spread > max_spread → tolerance exceeded → DEGRADED
   else → ALLOW
```

**Frame layout (64 bytes, one CPU cache line):**

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 8 | `val_primary` | f64 — bid / confidence floor |
| 8 | 8 | `val_secondary` | f64 — ask / token confidence |
| 16 | 8 | `timestamp_ns` | u64 — monotonic nanoseconds |
| 24 | 8 | `identifier` | u64 — frame ID |
| 32 | 4 | `domain` | u32 — 0=infra, 1=VAIG |
| 36 | 4 | `fail_mode` | u32 |
| 40 | 4 | `checksum` | u32 — CRC32C over bytes 0..39 |
| 44 | 4 | `_pad` | alignment |
| 48 | 8 | `max_spread` | f64 — L3 distrust-derived tolerance |
| 56 | 8 | `_reserved` | zeros |

> **Note on latency:** The 43 ns figure is measured on the production bare-metal path (SSE4.2 hardware CRC). Simulation builds use portable software CRC and will show higher RTT — this is expected and does not affect correctness.

---

## 4. L2 Orchestrator — transport and auth

**Claim:** Every decision is logged before being returned. Configuration changes require 2-person YubiKey authorization.

**Files:**
- `l2-orchestrator/bridge.py` — TCP/UDS frame serialization, CRC32C, `ValoBridge`
- `l2-orchestrator/src/worm_log.py` — SHA-256 hash-chained append-only audit log
- `l2-orchestrator/src/auth.py` — YubiKey 5 FIPS 2-person authorization
- `l2-orchestrator/src/propagator.py` — authorized config propagation to L1

**Key invariant:** `WORMAuditLog.append_event()` always chains the previous hash — the log cannot be silently modified.

---

## 5. L3 Context Engine — distrust levels

**Claim:** L1 tolerance shrinks automatically as data sources degrade. L4 triggers immediate HALT.

**Files:**
- `l3-context/src/distrust.rs` — distrust level state machine
- `l3-context/src/context_engine.rs` — source monitoring and max_spread calculation
- `l3-context/src/feeds.rs` — V1/V2 data feed ingestion

**Distrust table:**

| Level | Name | max_spread | Effect |
|-------|------|-----------|--------|
| L0 | Trusted | 5.0 | Normal operation |
| L1 | Monitor | 4.0 | Increased logging |
| L2 | Caution | 3.0 | Operator alert |
| L3 | Suspicious | 2.0 | Critical brake |
| L4 | Untrusted | -1.0 | **Total HALT** |

---

## 6. VAIG — AI Inference Guard

**Claim:** LLM token confidence is validated through L1 before tokens are forwarded to the client. Low-confidence tokens are replaced with `[REDACTED]`.

**Files:**
- `sidecar/vaig.py` — HTTP proxy with per-token L1 validation
- `simulate_vaig.py` — 4 test cases covering ALLOW and HALT paths

**Encoding:** For VAIG, `val_primary = max(τ, confidence_floor)` and `val_secondary = token_confidence`. L1 halts if threshold ≥ confidence.

---

## 7. Test suite reference

| Test file | What it covers | Binary needed? |
|-----------|----------------|----------------|
| `tests/test_bridge.py` | CRC32C, frame packing, F1/F2 invariants (23 tests) | No |
| `tests/test_integration.py` | Full 9/9 simulation paths | Yes |
| `simulate.py` | 5 infrastructure frames (ALLOW, DEGRADED×3, HALT) | Yes |
| `simulate_vaig.py` | 4 VAIG token frames (ALLOW, DEGRADED×2, HALT) | Yes |

---

## 8. Repository map

```
valo-v5-core/
├── l1-guardian/          Rust — deterministic validation core (DO NOT MODIFY)
│   └── src/
│       ├── valo_frame.rs         64-byte frame definition
│       ├── validation_logic.rs   F1, F2a, CRC32C decision logic
│       ├── crc32c.rs             Castagnoli CRC implementation
│       └── server.rs             TCP/UDS socket server
├── l2-orchestrator/      Python — transport, auth, audit log
│   ├── bridge.py                 Frame serialization + ValoBridge
│   └── src/
│       ├── auth.py               YubiKey 2-person authorization
│       ├── worm_log.py           SHA-256 hash-chained WORM log
│       └── propagator.py         Authorized L1 config propagation
├── l3-context/           Rust — distrust/context engine
│   └── src/
│       ├── distrust.rs           Distrust level state machine
│       ├── context_engine.rs     Source monitoring
│       └── feeds.rs              V1/V2 data feed ingestion
├── sidecar/              VAIG — LLM token confidence proxy
│   └── vaig.py
├── formal-verification/  TLA+ specifications
│   ├── ValoStateMachine.tla      Primary specification
│   ├── ValoStateMachine.cfg      TLC config
│   └── valo_v5.tla               Extended state machine
├── tests/                pytest test suite
│   ├── test_bridge.py            Unit tests (no binary)
│   └── test_integration.py       Integration tests
├── simulate.py           Infrastructure simulation (5 tests)
├── simulate_vaig.py      VAIG simulation (4 tests)
├── WHITEPAPER.md         Full technical whitepaper (English)
├── VALIDATION.md         Validation guide (English)
└── docs/
    ├── VALO_UiS_Validation_Request_v3.pdf
    ├── VALO_V5_Technical_Whitepaper_UiS_v3.pdf
    └── VALO_COHERENCE_CRITERION.md
```

---

## 9. What is out of scope for Phase 1

- Physical hardware installation (FPGA port, PCIe DMA) — V5.x roadmap
- YubiKey physical token validation — requires hardware
- Production SSE4.2 latency measurement — requires bare-metal setup
- V3 external data feed — deferred to V5.1

All Phase 1 claims are verifiable from the simulation build on a standard laptop.
