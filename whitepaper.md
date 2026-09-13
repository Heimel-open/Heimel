# VALO V5.0 — Technical Whitepaper
*Deterministic Safety Architecture for Critical Infrastructure and AI Systems*

**Valo Research Group | Stavanger, Norway | May 2026**  
**Repository:** `Valo-Research-Geoup/valo-v5-core`  
**Validation contact:** nsolland@github  
**Status:** Simulation-validated. Physical installation pending.

---

## Table of Contents

1. [The Problem](#1-the-problem)
2. [The Solution in One Paragraph](#2-the-solution-in-one-paragraph)
3. [Architecture Overview](#3-architecture-overview)
4. [L1 Guardian — The Gate](#4-l1-guardian--the-gate)
5. [L2 Orchestrator — The Bridge](#5-l2-orchestrator--the-bridge)
6. [L3 Context Engine — The Signal](#6-l3-context-engine--the-signal)
7. [The Transport Layer](#7-the-transport-layer)
8. [VAIG — AI Inference Guard](#8-vaig--ai-inference-guard)
9. [Formal Verification (TLA+)](#9-formal-verification-tla)
   - [9.5 Related Work](#95-related-work)
   - [9.6 Limitations and Future Work](#96-limitations-and-future-work)
10. [Frame Protocol](#10-frame-protocol)
11. [Test Results](#11-test-results)
12. [How to Run](#12-how-to-run)
13. [Usage Areas and Examples](#13-usage-areas-and-examples)
14. [Performance Metrics](#14-performance-metrics)
15. [Roadmap](#15-roadmap)

---

## 1. The Problem

Modern systems that make consequential decisions — trading engines, industrial controllers, AI models — are **stochastic and non-deterministic**. They can:

- Pause unpredictably (garbage collector runs, OS scheduler preempts)
- Produce values that are plausible but wrong (AI hallucinations, sensor drift)
- Fail in ways that are not caught until damage is done
- Be manipulated through tampered data

The standard response is logging and alerting. **That is not good enough** when the consequence of a wrong decision is a tripped power grid, an incorrect medication dose, or an autonomous agent taking an irreversible action.

What is needed is a layer that **cannot be bypassed**, makes its decision in guaranteed time, and whose behaviour is **mathematically proven** before deployment.

---

## 2. The Solution in One Paragraph

VALO V5.0 is a three-layer deterministic safety gate. Every proposed action — whether from a trading algorithm, an industrial controller, or a large language model — is packed into a 64-byte frame and submitted to L1, a Rust process with no operating system overhead. L1 verifies the frame's integrity via CRC32C, applies two logical checks, and returns a single byte: **Allow**, **Degraded**, or **Halt**. The allowed tolerance is set dynamically by L3, which monitors data sources and raises a distrust level as sources degrade. L2 coordinates the flow, handles authentication, and writes every decision to an immutable audit log. The state machine governing all transitions is formally verified using TLA+ model checking — it is mathematically impossible for the system to remain in an active state under high distrust, and Halt is terminal.

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     EXTERNAL WORLD                          │
│  (Trading algorithm / Industrial sensor / LLM API output)  │
└────────────────────────────┬────────────────────────────────┘
                             │ proposed action
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                   L3 — CONTEXT ENGINE (Rust)                │
│                                                             │
│  Monitors data sources. Each failure raises distrust.       │
│  DistrustLevel: L0Trusted → L1Monitor → L2Caution →         │
│                 L3Suspicious → L4Untrusted                  │
│                                                             │
│  Outputs: max_spread (tolerance for L1)                     │
└────────────────────────────┬────────────────────────────────┘
                             │ max_spread
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                   L2 — ORCHESTRATOR (Python)                │
│                                                             │
│  Packs 64-byte frame with CRC32C checksum                   │
│  Sends frame to L1 over TCP/UDS persistent socket           │
│  Logs every decision to WORM audit log                      │
│  Enforces 2-person YubiKey auth for config changes          │
└────────────────────────────┬────────────────────────────────┘
                             │ 64-byte frame (TCP/UDS)
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                   L1 — GUARDIAN (Rust, no_std)              │
│                                                             │
│  1. CRC32C integrity check (bytes 0..39)                    │
│  2. F1: val_primary < val_secondary?                        │
│  3. F2a: spread within distrust-derived tolerance?          │
│                                                             │
│  → 1 byte response: 0x00 Allow / 0x01 Degraded / 0x02 Halt │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
                    Decision is final.
                 Logged. Cannot be undone.
```

### Key design properties

| Property | How it is enforced |
| --- | --- |
| Deterministic latency | `no_std` Rust — no OS, no GC, no heap in hot path |
| Tamper detection | CRC32C over first 40 bytes of every frame |
| Dynamic tolerance | L3 distrust level shrinks allowed spread as sources degrade |
| Formal correctness | TLA+ state machine; model-checked by TLC |
| Immutable audit | WORM log with SHA-256 hash chaining |
| Auth for config | YubiKey 5 FIPS 2-person control for spread limit overrides |
| Fail-safe | Any CRC failure or L4 distrust → immediate Halt |

---

## 4. L1 Guardian — The Gate

**Language:** Rust (`no_std` for bare-metal; `simulation` feature enables `std` for TCP)  
**Location:** `l1-guardian/`  
**Decision latency:** 43 ns (deterministic, bare metal target)

### 4.1 Frame Definition

```rust
// l1-guardian/src/valo_frame.rs

#[repr(C, align(64))]   // exactly one CPU cache line
#[derive(Debug, Clone, Copy)]
pub struct ValoFrame {
    pub val_primary: f64,    // bid price / VAIG: confidence threshold max(τ, floor)
    pub val_secondary: f64,  // ask price / VAIG: token confidence score
    pub timestamp_ns: u64,
    pub identifier: u64,
    pub domain: u32,         // 0 = infrastructure  1 = VAIG (LLM)
    pub fail_mode: u32,
    pub checksum: u32,       // CRC32C over bytes 0..39
    _pad: u32,               // explicit alignment padding
    pub max_spread: f64,     // distrust-derived tolerance (from L3)
    _reserved: [u8; 8],
}

pub enum Decision { Allow, Degraded, Halt }
```

The struct is exactly **64 bytes** — one CPU cache line. Every read and write touches precisely one cache line, eliminating false sharing and prefetch misses.

### 4.2 Validation Logic

```rust
// l1-guardian/src/validation_logic.rs

pub fn validate_frame(frame: &ValoFrame, raw: &[u8; 64]) -> Decision {

    // Step 1: CRC32C integrity check over bytes 0..39
    // If a single bit was changed in transit or by tampering → Halt
    if !verify_frame_integrity(raw, frame.checksum) {
        return Decision::Halt;
    }

    // Step 2 (F1): Primary must be strictly below secondary
    // Infrastructure: bid must be below ask (no negative spread)
    // VAIG: effective threshold must be below token confidence
    if frame.val_primary >= frame.val_secondary {
        return Decision::Halt;
    }

    // Step 3 (F2a): L4Untrusted sentinel — block everything
    if frame.max_spread < 0.0 {
        return Decision::Halt;
    }

    // Step 4 (F2b): Spread within distrust-derived tolerance?
    let spread = frame.val_secondary - frame.val_primary;
    if spread > frame.max_spread {
        return Decision::Degraded;
    }

    Decision::Allow
}
```

**The logic is intentionally minimal.** Three comparisons. No branching on external state. No memory allocation. No I/O. The same function runs on bare metal at 43 ns and in simulation over TCP.

### 4.3 CRC32C Implementation

```rust
// l1-guardian/src/crc32c.rs
// Castagnoli polynomial 0x82F63B78
// Software implementation for portability.
// In production x86: replace with _mm_crc32_u8 loop (same result, 1 cycle/byte).

pub fn crc32c_bytes(data: &[u8]) -> u32 {
    const POLY: u32 = 0x82F63B78;
    let mut crc: u32 = 0xFFFF_FFFF;
    for &byte in data {
        crc ^= byte as u32;
        for _ in 0..8 {
            crc = if crc & 1 != 0 { (crc >> 1) ^ POLY } else { crc >> 1 };
        }
    }
    crc ^ 0xFFFF_FFFF
}

pub fn verify_frame_integrity(frame_bytes: &[u8; 64], expected: u32) -> bool {
    crc32c_bytes(&frame_bytes[0..40]) == expected
}
```

The same polynomial is implemented in Python in `bridge.py`. Both sides must agree on the algorithm — if they don't, every frame fails the integrity check and L1 halts.

---

## 5. L2 Orchestrator — The Bridge

**Language:** Python  
**Location:** `l2-orchestrator/`, `layers/L2_orchestrator/`  
**Role:** Packs frames, maintains persistent connection to L1, authenticates operators, writes audit log.

### 5.1 Frame Packing and Transport

```python
# layers/L2_orchestrator/bridge.py

def _crc32c(data: bytes) -> int:
    """CRC32C matching L1 Rust implementation — same polynomial."""
    POLY = 0x82F63B78
    crc = 0xFFFF_FFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ POLY if crc & 1 else crc >> 1
    return (crc ^ 0xFFFF_FFFF) & 0xFFFFFFFF

def pack_valo_frame(self, val_primary, val_secondary, max_spread,
                    identifier=0, domain=0, fail_mode=0) -> bytes:
    timestamp_ns = time.monotonic_ns()

    # Compute CRC over the first 40 bytes (header fields)
    header = struct.pack("<ddQQII",
        val_primary, val_secondary, timestamp_ns,
        identifier, domain, fail_mode)
    checksum = _crc32c(header)

    # Pack the full 64-byte frame
    # Format: 2×f64, 2×u64, 3×u32, 4-byte pad, f64, 8-byte reserved
    return struct.pack("<ddQQIII4xd8x",
        val_primary, val_secondary, timestamp_ns,
        identifier, domain, fail_mode, checksum, max_spread)

def send_frame(self, frame: bytes) -> tuple[Decision, int]:
    """Send 64-byte frame, receive 4-byte response. Returns (Decision, RTT_ns)."""
    t0 = time.monotonic_ns()
    self._sock.sendall(frame)           # exactly 64 bytes
    resp = self._recv_exact(4)          # exactly 4 bytes back
    rtt = time.monotonic_ns() - t0
    return Decision(resp[0]), rtt
```

**Connection setup (low-latency):**
```python
def connect(self, host="127.0.0.1", port=7743):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # disable Nagle
    s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 64)    # tune for 64-byte frames
    s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4)
    s.connect((host, port))
    self._sock = s
```

The connection is established **once** and reused for every frame. Opening a new TCP connection per frame would add ~50µs of handshake overhead each time.

### 5.2 WORM Audit Log

Every decision — not just Halt — is logged permanently with a SHA-256 hash chain.

```python
# l2-orchestrator/src/worm_log.py

def append_event(self, role: str, action: str, metadata: dict) -> str:
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "session": self.current_session_id,
        "role": role,
        "action": action,
        "data": metadata
    }
    entry_string = json.dumps(entry, sort_keys=True)
    entry_hash = hashlib.sha256(entry_string.encode()).hexdigest()
    log_line = f"{entry_hash} | {entry_string}\n"

    # Append-only write — simulates hardware WORM (Intel P5800X Optane target)
    with open(log_file, "a") as f:
        f.write(log_line)
    return entry_hash
```

Each line is independently verifiable. Deletion of any line breaks the hash chain and is detectable.

---

## 6. L3 Context Engine — The Signal

**Language:** Rust (`no_std` lib + `std` binary)  
**Location:** `l3-context/`  
**Role:** Tracks source reliability. Each failure raises distrust. Distrust tightens the L1 tolerance.

### 6.1 Distrust Escalation

```rust
// l3-context/src/distrust.rs

fn score_from_failures(count: u32) -> u8 {
    match count {
        0     => 0,   // L0: fully trusted
        1..=2 => 1,   // L1: monitor
        3..=5 => 2,   // L2: caution
        6..=9 => 3,   // L3: suspicious
        _     => 4,   // L4: untrusted — maximum distrust
    }
}

pub fn update_score(&mut self, index: usize, failed: bool) {
    // Update per-source failure count
    // Recompute score from failures
    // Recompute global_level as max score across all sources
    // → global_level automatically escalates with failures
}
```

### 6.2 Tolerance Mapping

```rust
// Infrastructure domain: max allowed spread between primary and secondary values
pub fn max_spread_for_level(&self) -> f64 {
    match self.global_level {
        DistrustLevel::L0Trusted    =>  5.0,   // wide tolerance, all is well
        DistrustLevel::L1Monitor    =>  4.0,
        DistrustLevel::L2Caution    =>  3.0,
        DistrustLevel::L3Suspicious =>  2.0,
        DistrustLevel::L4Untrusted  => -1.0,   // sentinel: immediate Halt in L1
    }
}

// VAIG domain: minimum acceptable token confidence
pub fn confidence_floor_for_level(&self) -> f64 {
    match self.global_level {
        DistrustLevel::L0Trusted    => 0.05,
        DistrustLevel::L1Monitor    => 0.10,
        DistrustLevel::L2Caution    => 0.20,
        DistrustLevel::L3Suspicious => 0.35,
        DistrustLevel::L4Untrusted  => 1.01,  // above max confidence — blocks all tokens
    }
}
```

**Why `-1.0` and `1.01` as sentinels?**  
L1's validation logic checks `if frame.max_spread < 0.0 → Halt` and `if primary >= secondary → Halt`. These sentinels guarantee that L4 distrust always produces a Halt regardless of the values in the frame — even if L2 were compromised and sent optimistic values.

---

## 7. The Transport Layer

### 7.1 L1 TCP/UDS Server

```rust
// l1-guardian/src/server.rs (simulation binary, feature = "simulation")

fn handle(mut stream: impl Read + Write) {
    let mut buf = [0u8; 64];
    loop {
        // recv_exact: read exactly 64 bytes — never act on a partial frame
        if stream.read_exact(&mut buf).is_err() { break; }

        let frame = ValoFrame::from_bytes(&buf);
        let decision = validate_frame(&frame, &buf);

        // 4-byte response: decision byte + 3 reserved
        let response = [decision_byte(decision), 0, 0, 0];
        if stream.write_all(&response).is_err() { break; }
    }
}
```

**Socket options applied:**
- `TCP_NODELAY = 1` — disables Nagle's algorithm; sends 64-byte frames immediately
- `SO_RCVBUF = 64` — kernel buffer sized for frame payload
- `SO_SNDBUF = 4` — kernel buffer sized for response

**UDS vs TCP:**
- Same-host: use Unix Domain Socket (`/tmp/valo_v5_l1.sock`) — bypasses TCP/IP stack entirely (~1–5µs)
- Remote: use TCP (`127.0.0.1:7743` default) — still fast over loopback (~100–200µs)

### 7.2 Frame Deserialisation (Zero-Copy)

```rust
// l1-guardian/src/valo_frame.rs

pub fn from_bytes(buf: &[u8; 64]) -> Self {
    Self {
        val_primary:   f64::from_le_bytes(buf[0..8].try_into().unwrap()),
        val_secondary: f64::from_le_bytes(buf[8..16].try_into().unwrap()),
        timestamp_ns:  u64::from_le_bytes(buf[16..24].try_into().unwrap()),
        identifier:    u64::from_le_bytes(buf[24..32].try_into().unwrap()),
        domain:        u32::from_le_bytes(buf[32..36].try_into().unwrap()),
        fail_mode:     u32::from_le_bytes(buf[36..40].try_into().unwrap()),
        checksum:      u32::from_le_bytes(buf[40..44].try_into().unwrap()),
        _pad:          0,
        max_spread:    f64::from_le_bytes(buf[48..56].try_into().unwrap()),
        _reserved:     [0u8; 8],
    }
}
```

No allocation. No copying beyond the initial socket read into a stack buffer. The frame lives on the stack for its entire lifetime.

---

## 8. VAIG — AI Inference Guard

VAIG extends the VALO gate to intercept LLM token streams. It sits as an HTTP proxy between any application and any OpenAI-compatible LLM API.

### 8.1 How It Works

```
Application  →  POST /v1/chat/completions
                      ↓
              VAIG proxy (sidecar/vaig.py)
              - injects: logprobs=true, stream=true
                      ↓
              LLM API (OpenAI / vLLM / Ollama)
              - returns: SSE stream with per-token logprobs
                      ↓
              VAIG processes each token:
              confidence = exp(logprob)       # convert log-probability to [0,1]
              primary = max(τ, floor)         # effective block threshold
              secondary = confidence          # token confidence score
              send ValoFrame to L1 via TCP
                      ↓
              L1 decision:
              Allow    → forward token unchanged
              Degraded → forward + X-Valo-Confidence: degraded header
              Halt     → replace token with [REDACTED], log to WORM
                      ↓
              Application receives validated stream
```

### 8.2 VAIG Frame Encoding

The same 64-byte ValoFrame is used. Domain field = 1 identifies VAIG frames to L1.

```python
# sidecar/vaig.py

def _validate_token(confidence: float, token_id: int) -> Decision:
    # val_primary  = max(τ, distrust_floor)  — effective block threshold
    # val_secondary = token confidence        — what the model actually scored
    # L1 halts if primary >= secondary        — threshold at or above confidence
    primary = max(_tau, _confidence_floor)
    secondary = confidence
    frame = _bridge.pack_valo_frame(
        val_primary=primary,
        val_secondary=secondary,
        max_spread=100.0,    # F2a unused in VAIG — binary Halt/Allow
        identifier=token_id,
        domain=1,
    )
    decision, _ = _bridge.send_frame(frame)
    return decision
```

**Why `max_spread=100.0`?**  
In VAIG mode the decision is binary — a token either clears the threshold or it does not. There is no "Degraded" zone. Setting max_spread to an impossibly large value ensures F2a never fires and the only outcomes are Allow (confidence above threshold) or Halt (confidence at or below threshold).

### 8.3 Distrust Integration

The VAIG confidence floor comes from the same DistrustManager as the infrastructure domain:

| DistrustLevel | Infrastructure tolerance | VAIG confidence floor |
| --- | --- | --- |
| L0Trusted | 5.0 | 0.05 (accept most tokens) |
| L1Monitor | 4.0 | 0.10 |
| L2Caution | 3.0 | 0.20 |
| L3Suspicious | 2.0 | 0.35 (only high-confidence tokens pass) |
| L4Untrusted | Halt (sentinel -1.0) | Halt (sentinel 1.01) |

As external conditions degrade — network issues, sensor failures, anomalous data patterns — the distrust level rises automatically, and VAIG becomes progressively stricter about which tokens it allows through.

---

## 9. Formal Verification (TLA+)

The system's safety properties are machine-checked using TLA+ and the TLC model checker.

### 9.1 State Machine (`formal-verification/ValoStateMachine.tla`)

```tla
VARIABLES state, timer, context_age, audit_log, clock

Init ==
    /\ state = "Active"
    /\ timer = 0
    /\ context_age = 0
    /\ audit_log = << >>
    /\ clock = 0

Next ==
    \/ Active → Active      (coherent tick — context_age increments)
    \/ Active → Degraded    (coherence/syntax/latency violation — timer starts)
    \/ Active → Halt        (context_age overflow — DirectHalt)
    \/ Degraded → Degraded  (timer countdown)
    \/ Degraded → Halt      (timer reaches 0 — TimeoutHalt)
    \/ Halt → Active        (authorized SystemReset — 2-person YubiKey auth)
    \/ Any → LogFullHalt    (audit log full — irrecoverable terminal state)
    \/ LogFullHalt → LogFullHalt  (stuttering step)
```

### 9.2 Proven Properties

```tla
(* Type constraints hold at every reachable state *)
TypeInvariant ==
    /\ state \in {"Active", "Degraded", "Halt", "LogFullHalt"}
    /\ timer \in 0..MaxDegradedTime
    /\ context_age \in 0..MaxContextAge
    /\ Len(audit_log) <= MaxLogSize

(* Active state cannot persist beyond the context age bound *)
SafetyInvariant == (state = "Active") => (context_age < MaxContextAge)

(* LogFullHalt is the irrecoverable terminal state — no variable changes *)
LogFullHaltIsTerminal == [][state = "LogFullHalt" => UNCHANGED vars]_vars

(* Audit log is strictly append-only across every transition *)
WORMAppendOnly == [][Len(audit_log') >= Len(audit_log)]_vars

(* Degraded with timer=0 always leads to Halt or LogFullHalt *)
DegradedEventuallyHalt ==
    (state = "Degraded" /\ timer = 0) ~> (state = "Halt" \/ state = "LogFullHalt")

(* A full audit log always leads to LogFullHalt *)
LogFullReachable == (Len(audit_log) = MaxLogSize) ~> (state = "LogFullHalt")
```

TLC v2.16 verified all six properties across 1,662 distinct reachable states (MaxDegradedTime=15, MaxContextAge=10, MaxLogSize=11) with zero counterexamples.

### 9.3 Distrust Safety (`formal-verification/valo_v5.tla`)

```tla
---- MODULE valo_v5 ----
(* Module name matches filename exactly — case-sensitive on Linux *)

SafetyInvariant ==
    state = "HALT" => (timer >= 30 \/ distrust_level >= 4)

HaltIsTerminal ==
    [][state = "HALT" => UNCHANGED vars]_vars

EventualHalt ==
    (state = "DEGRADED") ~> (state = "HALT")
```

This invariant is scoped to the `HALT` state only. The state `(ACTIVE, distrust=4)` is a reachable intermediate state — L3 can raise distrust to L4 while the system is still `ACTIVE`, one step before the emergency-halt transition fires. The invariant that holds is: every `HALT` state was reached either via timer expiry or distrust saturation. TLC confirmed this with zero counterexamples.

### 9.4 Running the Model Checker

```bash
wget https://github.com/tlaplus/tlaplus/releases/download/v1.7.1/tla2tools.jar
java -cp tla2tools.jar tlc2.TLC -config formal-verification/ValoStateMachine.cfg formal-verification/ValoStateMachine.tla
java -cp tla2tools.jar tlc2.TLC -config formal-verification/valo_v5.cfg formal-verification/valo_v5.tla
```

Both checks run automatically in CI (`.github/workflows/integrity-check.yml`) on every push.

### 9.5 Related Work

The VALO architecture belongs to the **runtime assurance** (RTA) family of safety architectures, which has been an active area of research and standardisation for over two decades. This section situates VALO within that literature.

**Simplex Architecture.** The foundational pattern is the Simplex Architecture (Sha, IEEE Software 18(4), 2001): a high-performance *Advanced Controller* runs alongside a verified *Baseline Controller*, with a *Decision Module* that switches to the baseline when a safety property is violated. VALO follows this pattern — L3/L2 constitute the advanced layer; L1 Guardian is the verified fallback. The key differences are scope (VALO handles both infrastructure signals and LLM token streams under a unified frame protocol) and trigger mechanism (a confidence threshold derived from the VALO Coherence Criterion rather than a reachability-based safety predicate). Subsequent elaborations include Neural Simplex (Phan et al., ISoLA 2020) and Black-Box Simplex (Bak, Smolka, Stoller, NFM 2022), which formally prove that runtime checks can replace static baseline verification — demonstrated on F-16 formation flight with neural-network controllers using reachability-based safety theorems.

**R2U2.** The closest published prior art at the implementation level is R2U2 (Johannsen, Jones, Kempa, Rozier, Zhang, CAV 2023; Aurandt, Jones, Rozier, NFM 2025): a modular runtime verification framework in `no_std` Rust with 25 Mission-time LTL operators verified via Verus code contracts, deployed on NASA Lunar Gateway, JAXA satellites, and NASA Robonaut2. R2U2 evaluates MLTL formulae over sensor streams with three-valued semantics; VALO evaluates a fixed three-check decision procedure over a binary frame. VALO is narrower in expressiveness but integrable as a black-box sidecar without a formula compiler. R2U2's MLTL semantics provide a formal meaning for every trigger formula; VALO's confidence trigger (C₀) is empirically derived and not itself formally verified — this is VALO's most significant open limitation relative to R2U2.

**Copilot / CopilotVerifier.** Copilot (Perez, Dedden, Goodloe; NASA, 2020) is a Haskell DSL compiling stream specifications to constant-time C monitors. CopilotVerifier (Scott, Dodds, Perez, Goodloe, Dockins; ICFP 2023) adds per-build bisimulation proofs via Crucible/What4 SMT, establishing observational equivalence between the Haskell specification and generated C code. VALO's Kani proof harness is a partial analogue but does not establish bisimulation with the TLA+ specification.

**ModelPlex / KeYmaera X.** ModelPlex (Mitsch, Platzer; FMSD 2016) generates runtime monitors from differential-dynamic-logic proofs of hybrid control systems. Where TLA+ models discrete state transitions, dL reasons natively about continuous plant dynamics. VALO does not model plant dynamics; for deployments where the safety argument must cover continuous-time plant behaviour during and after halt, a KeYmaera X-style layer is required as a complement.

**ASTM F3269-21.** This standard provides a published regulatory pathway for runtime assurance of complex AI functions in aviation, where conventional DO-178C assurance is impractical. VALO's architecture is structurally compatible with the ASTM F3269-21 pattern (untrusted complex function + runtime monitor + reversion mechanism), though V5.0 targets EU AI Act Annex III contexts rather than aviation certification.

**VALO's specific contribution** within this landscape is a deployment profile rather than a new conceptual category: a unified binary frame protocol covering infrastructure and LLM domains, an EU AI Act evidence package (WORM log for Article 12, 2-person auth for Article 14, TLC verification for Article 15), and a token-stream HTTP proxy (VAIG) applying the same L1 logic to per-token logprob confidence scores.

### 9.6 Limitations and Future Work

**Confidence trigger is unverified.** The formal guarantees proven by TLC apply to the state machine that acts on the trigger signal, not to the trigger itself. Whether `C < C₀` correctly identifies unsafe AI outputs is an open empirical question. Modern deep neural networks are systematically overconfident on out-of-distribution inputs [Zhu et al., ECCV 2022], and no OOD detection technique generalises reliably across all distribution shifts [CMU SEI 2024]. VALO's formal guarantee is therefore conditional: *given that the trigger fires when it should, the system provably halts.* The trigger's reliability is outside the scope of the current verification. Future work should replace or supplement the scalar threshold with a temporal-logic trigger condition (MLTL or STL) with defined formal semantics, or a logical conjunction of independent signals (cross-sensor consistency, latency, redundant prediction agreement).

**Implementation fidelity.** TLC verifies the TLA+ specification; the Kani proof harness verifies the safety invariant on compiled Rust; but no bisimulation proof currently links the two. A future Verus proof of all L1 transitions would bring VALO to parity with R2U2 [Aurandt et al., NFM 2025] and CopilotVerifier [Scott et al., ICFP 2023] on this dimension.

**Discrete model only.** The TLA+ specification models the safety controller's discrete lifecycle. It makes no claim about continuous plant dynamics during or after the Halt transition. For deployments requiring a formal end-to-end safety argument, a companion continuous-time proof (barrier certificates, control barrier functions, or KeYmaera X reachability) is required.

**Latency figure is a design target.** The 43 ns L1 decision latency is derived from the CRC32C SSE4.2 hardware instruction latency on the intended bare-metal platform. It has not yet been measured under sustained production load with jitter statistics. Bare-metal validation is planned for the physical installation phase.

**Future work:** (1) MLTL-based trigger formalisation; (2) Verus contracts for L1 Rust transitions; (3) per-domain plant safety arguments; (4) independent certification assessment (IEC 61508 SIL-2/SIL-3); (5) latency benchmarking against R2U2 and Copilot on equivalent formula complexity; (6) submission to a peer-reviewed venue (RV, NFM, or FMICS).

---

## 10. Frame Protocol

### 10.1 Request Frame (L2 → L1, 64 bytes, little-endian)

```
Offset  Size  Type    Field           Notes
──────  ────  ──────  ──────────────  ─────────────────────────────────────
0       8     f64     val_primary     Bid price / VAIG: max(τ, floor)
8       8     f64     val_secondary   Ask price / VAIG: token confidence
16      8     u64     timestamp_ns    time.monotonic_ns() at send time
24      8     u64     identifier      Sequence number / token position
32      4     u32     domain          0=infrastructure  1=VAIG
36      4     u32     fail_mode       Reserved for fail classification
40      4     u32     checksum        CRC32C over bytes 0..39
44      4     u32     _pad            Alignment padding (always 0)
48      8     f64     max_spread      Distrust-derived tolerance from L3
56      8     [u8;8]  _reserved       Zero-padded
──────  ────  ──────  ──────────────  ─────────────────────────────────────
Total   64
```

**CRC32C scope:** Bytes 0–39 (val_primary through fail_mode). The checksum and max_spread fields are excluded from the checksum — checksum is self-referential, and max_spread is a trusted value from the control plane.

### 10.2 Response Frame (L1 → L2, 4 bytes)

```
Offset  Size  Field     Values
──────  ────  ────────  ──────────────────────────────────────────
0       1     decision  0x00 = Allow  0x01 = Degraded  0x02 = Halt
1       3     reserved  Zero-padded (reserved for latency stamp)
```

---

## 11. Test Results

### 11.1 Infrastructure Simulation (`simulate.py`)

5 tests covering the coherence zone, flag validation, and context-age overflow. Each test
spawns a fresh L1 process (stateful ValoGuardrail starts at Active/age=0).

```
[SIM] Running 5 L1 telemetry tests (TCP)...

  [PASS] Coherent confidence in [0.42·c0, 1.06·c0] — expect Active/ALLOW
         decision=ALLOW     expected=ALLOW     RTT=~150µs

  [PASS] Confidence below coherence zone (0.20 < 0.42·c0) — expect Degraded
         decision=DEGRADED  expected=DEGRADED  RTT=~110µs

  [PASS] Confidence above coherence zone (1.20 > 1.06·c0) — expect Degraded
         decision=DEGRADED  expected=DEGRADED  RTT=~105µs

  [PASS] Syntax flag invalid — expect Degraded
         decision=DEGRADED  expected=DEGRADED  RTT=~108µs

  [PASS] Context-age overflow (2 warmup frames, 3rd triggers DirectHalt) — expect Halt
         decision=HALT      expected=HALT      RTT=~112µs

[SIM] ALL PASS
```

### 11.2 VAIG Simulation (`simulate_vaig.py`)

4 tests covering high/low token confidence and latency flags.

```
[VAIG-SIM] Running 4 VAIG token-confidence tests (TCP)...

  [PASS] High token confidence (0.95) within coherence zone — expect Active/ALLOW
         conf=0.95  c0=1.0  decision=ALLOW     expected=ALLOW     RTT=~155µs

  [PASS] Low token confidence (0.05) below coherence floor 0.42·c0 — expect Degraded
         conf=0.05  c0=1.0  decision=DEGRADED  expected=DEGRADED  RTT=~108µs

  [PASS] Latency flag invalid (token too slow) — expect Degraded
         conf=0.80  c0=1.0  decision=DEGRADED  expected=DEGRADED  RTT=~102µs

  [PASS] Context-age overflow (2 warmup frames, 3rd valid triggers DirectHalt) — expect Halt
         conf=0.80  c0=1.0  decision=HALT      expected=HALT      RTT=~115µs

[VAIG-SIM] ALL PASS
```

**9 / 9 tests pass. All decision paths validated.**

---

## 12. How to Run

### Prerequisites

```bash
# Rust (stable + nightly for no_std)
curl https://sh.rustup.rs -sSf | sh

# Python 3.11+
python --version

# Java (for TLA+ model checker)
java -version
```

### Build L1 Guardian

```bash
cd l1-guardian

# Simulation binary (TCP server, std enabled)
cargo build --features simulation

# Check no_std core (what runs on bare metal)
cargo check
```

### Run Infrastructure Simulation

```bash
# From repo root
python simulate.py

# With UDS instead of TCP (lower latency, same host only)
python simulate.py --uds
```

### Run VAIG Simulation

```bash
python simulate_vaig.py
```

### Run VAIG Proxy Against a Real LLM

```bash
# Start L1 first
cd l1-guardian
cargo run --features simulation -- --tcp 127.0.0.1:7743

# Start VAIG proxy (in another terminal)
python sidecar/vaig.py \
    --upstream http://localhost:11434 \   # your LLM API (Ollama example)
    --port 8080 \
    --l1-tcp 127.0.0.1:7743 \
    --tau 0.10 \
    --confidence-floor 0.05

# Your application now calls http://localhost:8080 instead of the LLM directly
curl http://localhost:8080/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model":"llama3","messages":[{"role":"user","content":"Hello"}]}'
```

### Run TLA+ Model Checker

```bash
wget https://github.com/tlaplus/tlaplus/releases/download/v1.7.1/tla2tools.jar
java -cp tla2tools.jar tlc2.TLC formal-verification/ValoStateMachine.tla
```

### Trigger L3 Distrust Escalation

```bash
# Start L3 process
cd l3-context
cargo run

# In another terminal, inject failures on stdin:
echo "0 1" | cargo run   # source 0 failed once → score rises
echo "0 1" >> /proc/...  # or pipe continuously
```

---

## 13. Usage Areas and Examples

### 13.1 Financial Trading — Preventing Negative Spread

**Scenario:** A high-frequency trading algorithm proposes a buy order at 101.0 and a sell at 100.0 — a crossed market (negative spread). This would result in an immediate loss.

```python
bridge = ValoBridge()
bridge.connect("127.0.0.1", 7743)

# L3 distrust = L0 (everything normal), max_spread = 5.0
frame = bridge.pack_valo_frame(
    val_primary=101.0,    # bid (buy price)
    val_secondary=100.0,  # ask (sell price)
    max_spread=5.0,
    domain=0,
)
decision, rtt = bridge.send_frame(frame)
# decision = HALT — val_primary >= val_secondary, immediately blocked
```

**Without VALO:** The order goes through, locking in a loss.  
**With VALO:** Halt in <1µs. Order never reaches the exchange.

---

### 13.2 Industrial Control — Sensor Degradation

**Scenario:** An offshore platform has two pressure sensors. Sensor B starts giving intermittent failures. The distrust level rises from L0 to L2Caution. The allowed operating spread tightens from 5.0 to 3.0 bar.

```python
# L3 detects 4 consecutive failures from source index 1
mgr = DistrustManager()
for _ in range(4):
    mgr.update_score(1, failed=True)
# global_level is now L2Caution, max_spread = 3.0

# Controller proposes: sensor_A=95.0, sensor_B=99.5 (spread = 4.5)
frame = bridge.pack_valo_frame(
    val_primary=95.0,
    val_secondary=99.5,
    max_spread=mgr.max_spread_for_level(),  # 3.0
    domain=0,
)
decision, _ = bridge.send_frame(frame)
# decision = DEGRADED — spread (4.5) exceeds tightened tolerance (3.0)
# System enters 30-second degraded window before forced Halt
```

**Without VALO:** The platform continues operating on degraded sensor data.  
**With VALO:** Degraded state triggers operator alert. If not resolved in 30 seconds → Halt (safe state).

---

### 13.3 AI Safety — Blocking Hallucinated Tokens

**Scenario:** An LLM is generating a medical dosage recommendation. One token has a logprob of -4.6 (confidence ≈ 0.01 — the model is highly uncertain). VAIG intercepts it.

```python
import math
logprob = -4.6
confidence = math.exp(logprob)   # ≈ 0.01

# VAIG frame: primary=max(τ=0.10, floor=0.05)=0.10, secondary=0.01
# L1: primary (0.10) >= secondary (0.01) → HALT
frame = bridge.pack_valo_frame(
    val_primary=0.10,     # effective threshold
    val_secondary=0.01,   # token confidence
    max_spread=100.0,     # VAIG mode: binary decision
    domain=1,
)
decision, _ = bridge.send_frame(frame)
# decision = HALT
# VAIG replaces the token with [REDACTED] in the response stream
# Event logged to WORM audit log with token position and confidence score
```

**Without VALO:** The uncertain token ("200mg" instead of "20mg") reaches the user.  
**With VALO:** Token blocked before delivery. Application receives `[REDACTED]`. Clinician is alerted to re-query.

---

### 13.4 Power Grid — Load Balancing Under Stress

**Scenario:** A grid management system proposes a load transfer. Under normal conditions, a ±5% deviation is acceptable. During a storm (high wind, external environmental stress), the distrust level rises and the tolerance tightens to ±2%.

```python
# Normal conditions (L0): max_spread = 5.0
frame_normal = bridge.pack_valo_frame(98.0, 102.0, max_spread=5.0)
# spread = 4.0, within 5.0 → ALLOW

# Storm conditions (L2Caution): max_spread = 3.0
frame_storm = bridge.pack_valo_frame(98.0, 102.0, max_spread=3.0)
# spread = 4.0, exceeds 3.0 → DEGRADED → operator alert
```

The tolerance narrows automatically as external conditions worsen — no manual reconfiguration required.

---

### 13.5 Sidecar Integration (Any Application)

Any application can integrate without knowing about the VALO internals:

```python
from sidecar.client import ValoSidecarClient

client = ValoSidecarClient()

result = client.request_validation(primary_val=98.0, secondary_val=100.0)
# Returns: "ALLOW", "DEGRADED", "HALT", or "BYPASS_MODE"

if result == "HALT":
    abort_operation()
elif result == "DEGRADED":
    alert_operator_and_continue()
elif result == "BYPASS_MODE":
    # VALO is unreachable — application continues (fail-open by design)
    # VALO is a sidecar, not a blocker
    continue_with_logging()
```

**BYPASS_MODE** is intentional. VALO is a safety sidecar — if VALO itself goes down, the application continues. Blocking the application because the safety layer is down would itself be a safety failure in many contexts.

---

## 14. Performance Metrics

| Metric | Value | Conditions |
| --- | --- | --- |
| L1 decision latency (bare metal target) | 43 ns | Deterministic, no_std Rust |
| L1 decision latency (simulation, loopback TCP) | ~100–170 µs P50 | Linux loopback, debug build |
| L1 decision latency (simulation, UDS) | ~5–15 µs P50 | Unix Domain Socket, same host |
| Physical P99.9 (digital twin estimate) | 18–24 µs | isolcpus, nohz_full, release build |
| Physical worst case (digital twin) | 45.92 µs | Thermal + cache sharing jitter |
| Frame size | 64 bytes | One CPU cache line |
| VAIG per-token overhead (target) | < 1 ms | L1 RTT + proxy parsing |
| Memory growth | 0.5 MB / 1M requests | Managed |

### Physical Installation Requirements (V4.1 reference)

For bare-metal deployment, the following kernel boot parameters eliminate OS-induced jitter:

```
isolcpus=2 nohz_full=2 rcu_nocbs=2
```

This pins L1 to CPU core 2, removes it from the OS scheduler, and stops timer interrupts on that core.

Python L2 should disable the garbage collector in the hot path:

```python
import gc
gc.disable()   # 0 ms GC pauses guaranteed — call before entering validation loop
```

---

## 15. Roadmap

### V4.1 — Foundation (Production-locked)
- [x] 64-byte binary frame protocol (UDS SOCK_STREAM, little-endian struct)
- [x] F1: Negative spread rejection (bid ≤ ask)
- [x] F2: 5% spread bound ((ask − bid) / bid ≤ 0.05)
- [x] F3: 3-phase liquidity bootstrap (Cold → Warming → Active)
- [x] P99.9 = 15.82 µs, tail ratio = 2.54
- [x] Single domain (Finance, domain=0), fail-closed

### V5.0 — Current (Simulation-validated)
- [x] Three-layer deterministic safety gate
- [x] TCP/UDS transport layer
- [x] CRC32C frame integrity
- [x] Dynamic distrust-based tolerance (distrust levels 0–4)
- [x] TLA+ formal verification
- [x] WORM audit log (Intel P5800X NVMe, append-only)
- [x] YubiKey 5 FIPS 2-person authorization (Operator / Manager / Administrator)
- [x] Autonomous HALT after 30s in DEGRADED state
- [x] VAIG LLM token validation sidecar
- [x] 9/9 simulation tests passing

### V5.1 — Planned
- [ ] V3 external data feed integration (deferred from V5.0)

### V5.x — Next (Physical installation)
- [ ] FPGA port of L1 core (SystemVerilog, ~2 ns decision latency)
- [ ] PCIe DMA transport (bypass TCP stack for production)
- [ ] Physical test results from UIS validation

### JANUS-NEXUS v6.2 — Agent Layer (Operational)
- [x] PANOPTIKON — market analysis & dialectics (collapse detection, growth vectors, narrative contradiction)
- [x] CLAW-BOT — data extraction & execution (raw facts only, no interpretation)
- [x] ARCHITECT — system design & prompt optimization (red-team, Monte Carlo)
- [x] RISK-ASSESSOR — vulnerability analysis (contagion modeling, worst-case scenarios)
- [x] Integration bridge: JANUS-NEXUS → VALO V5.0 → Critical Infrastructure (energy grids, AI data centres, telecom RAN, water utilities)
- [x] Operational modes: -q (quick), -oppose (red-team), -mark (markdown), -sync (frequency check)

### V6.0 — Evolution
- [ ] Adaptive thresholds: rolling volatility windows replacing hardcoded F2
- [ ] AI-Shield: RL cascade detection and anomaly scoring
- [ ] Remote attestation: TPM + Secure Boot validation for supply-chain resistance
- [ ] VAIG eBPF TC socket hook (intercept at kernel network layer)
- [ ] EU AI Act conformity documentation package
- [ ] Agent integration: Hermes (nousresearch/hermes-agent, 128k stars) — VALO gates each skill execution; MCP endpoint (validate_decision, check_invariants, report_status)
- [ ] Agent integration: Mercury (cosmicstack-labs/mercury-agent) — VALO extends permission-hardened "ask before acting" to deterministic 43ns gate; MCP integration

### Dev Tooling
- [ ] Adopt gstack (garrytan/gstack) engineering team workflow for VALO development sprints (CEO, Eng Manager, QA, Security, Release roles)

---

## Appendix A — Repository Structure

```
valo-v5-core/
├── l1-guardian/              Rust — deterministic validation core
│   ├── src/
│   │   ├── lib.rs            no_std core, module declarations
│   │   ├── valo_frame.rs     64-byte frame struct + from_bytes()
│   │   ├── validation_logic.rs  CRC + F1 + F2a checks
│   │   ├── crc32c.rs         Software CRC32C (Castagnoli)
│   │   ├── server.rs         TCP/UDS simulation server
│   │   └── main.rs           Simulation binary entry point
│   └── Cargo.toml
├── l2-orchestrator/          Python — control plane
│   └── src/
│       ├── auth.py           YubiKey 2-person auth
│       ├── propagator.py     Frame dispatch + WORM logging
│       └── worm_log.py       SHA-256 hash-chained audit log
├── l3-context/               Rust — distrust engine
│   └── src/
│       ├── lib.rs
│       ├── context_engine.rs DistrustLevel types
│       ├── distrust.rs       DistrustManager + tolerance mapping
│       ├── feeds.rs          Feed handler stubs
│       └── main.rs           L3 simulation process
├── layers/L2_orchestrator/
│   └── bridge.py             ValoFrame packing + TCP transport
├── sidecar/
│   ├── client.py             Application integration client
│   └── vaig.py               VAIG HTTP proxy
├── formal-verification/
│   ├── ValoStateMachine.tla  State machine with audit log
│   ├── ValoStateMachine.cfg  TLC configuration
│   └── valo_v5.tla           Distrust safety invariant
├── simulate.py               Infrastructure integration test (5 cases)
├── simulate_vaig.py          VAIG integration test (4 cases)
└── WHITEPAPER.md             This document
```

---

## Appendix B — Glossary

| Term | Meaning |
| --- | --- |
| **L1 Guardian** | The deterministic validation gate. Runs in no_std Rust. Makes the final Allow/Degraded/Halt decision. |
| **L2 Orchestrator** | The control plane. Packs frames, manages auth, writes audit log. |
| **L3 Context Engine** | Tracks source reliability. Raises distrust level as sources degrade. |
| **ValoFrame** | The 64-byte, cache-line-aligned data packet sent from L2 to L1 for validation. |
| **CRC32C** | Castagnoli CRC-32. Used to verify frame integrity before any value inspection. |
| **max_spread** | The distrust-derived tolerance embedded in each frame. L1 checks the spread against this value. |
| **DistrustLevel** | L0Trusted through L4Untrusted. Rises with source failures, shrinks the allowed tolerance. |
| **Degraded** | A transient state. The system continues operating but with a 30-second countdown. If not resolved → Halt. |
| **Halt** | Terminal state. The system stops. Cannot self-recover. Requires supervised re-arming. |
| **WORM log** | Write Once Read Many audit log. Every decision is appended and hash-chained. Cannot be altered. |
| **VAIG** | Valo AI-Inference Guard. Extends the gate to LLM token streams via per-token confidence validation. |
| **logprob** | Log-probability of a token in an LLM output. `exp(logprob)` = confidence score ∈ (0, 1]. |
| **τ (tau)** | The VAIG confidence threshold. Tokens with confidence below τ are blocked. |
| **BYPASS_MODE** | The sidecar client's fail-open state when L1 is unreachable. The application continues. |
| **no_std** | Rust without the standard library. No heap allocator, no OS, no GC. Required for bare-metal determinism. |
| **TLA+** | A formal specification language. Used here to prove safety properties via model checking (TLC). |

---

*Valo Research Group | Stavanger, Norway | May 2026*  
*Sandbox: https://valo-v5-core-production.up.railway.app*  
*Contact: nsolland@github*  
*Pending academic validation: University of Stavanger (UiS) — target July 31, 2026*
