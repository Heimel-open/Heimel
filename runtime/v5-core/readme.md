# VALO V5.0 — Deterministic Digital Kill Switch (Extended Matrix) ✅

[![VALO V5.0 Verification](https://github.com/Valo-Research-Geoup/valo-v5-core/actions/workflows/verify.yml/badge.svg)](https://github.com/Valo-Research-Geoup/valo-v5-core/actions/workflows/verify.yml)
[![TLA+ Model Check](https://github.com/Valo-Research-Geoup/valo-v5-core/actions/workflows/integrity-check.yml/badge.svg)](https://github.com/Valo-Research-Geoup/valo-v5-core/actions/workflows/integrity-check.yml)
[![CodeQL](https://github.com/Valo-Research-Geoup/valo-v5-core/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/Valo-Research-Geoup/valo-v5-core/security/code-scanning)
[![Security Risk Assessment](https://github.com/Valo-Research-Geoup/valo-v5-core/actions/workflows/github-code-scanning/code-security-risk-assessment/badge.svg)](https://github.com/Valo-Research-Geoup/valo-v5-core/security)
[![Formally Verified](https://img.shields.io/badge/TLA%2B-formally%20verified-brightgreen)](formal-verification/ValoStateMachine.tla)
[![Rust](https://img.shields.io/badge/L1%20core-Rust%20stable-orange?logo=rust)](l1-guardian/)

**Formally-Verified Graceful Fallback for Critical Infrastructure**

**Status:** TLC VALIDATION PASSED (specification-level) · v5.0.0 — see badges above for live CI state

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  VAIG Sidecar  (sidecar/vaig.py)                    │  ← HTTP proxy, per-token confidence gate
│  MCP Server    (mcp_server.py)                      │  ← AI assistant integration (Claude/Copilot)
└────────────────────────┬────────────────────────────┘
                         │  InferenceTelemetryPacket (18 bytes, big-endian)
┌────────────────────────▼────────────────────────────┐
│  L2 Orchestrator  (l2-orchestrator/)                │  ← Transport-agnostic bridge + WORM logger
│  Transport: TCP 127.0.0.1:7743  or  UDS socket      │
└────────────────────────┬────────────────────────────┘
                         │  TCP / Unix Domain Socket
┌────────────────────────▼────────────────────────────┐
│  L1 Guardian  (l1-guardian/, Rust)                  │  ← 43 ns CRC32C + FSM · TLA+-verified
│  States: Active → Degraded → Halt → LogFullHalt     │
└─────────────────────────────────────────────────────┘
```

## The Problem

Critical infrastructure operators deploy AI for real-time decisions. When something goes wrong, they need one guarantee: **The system will provably stop when told to stop.**

Not eventually. Not probably. **Provably.**

VALO solves this. When confidence drops below threshold, VALO formally guarantees:
- ✅ System halts deterministically (no timeouts, no hangs)
- ✅ LogFullHalt is the proven terminal state; Halt is recoverable only via authorized 2-person reset
- ✅ Audit log is immutable (WORM — Write Once Read Many)
- ✅ All transitions are atomic and traceable

## Validation Results

Tool: TLC Model Checker v2.16 (rev: cdddf55)
Result: Model checking completed. No error found.
Date: 2026-05-19T05:37:59Z
Scope: Exhaustive state-space validation (full run: MaxDegradedTime=15, MaxContextAge=10, MaxLogSize=11)

## Key Metrics

| Metric | Value |
|--------|-------|
| States Generated | 2 124 |
| Distinct States Found | **1 662** |
| State Graph Depth | **13** |
| Verification Time | < 1 second |
| Counterexamples Found | 0 (0 states left on queue) |

> **Note:** Previous runs cited 4,782,943 states — that figure was from an earlier spec version
> (3-state machine, Halt terminal, no LogFullHalt or SystemReset). The current spec adds
> LogFullHalt as the true terminal state and authorized SystemReset (Halt → Active), which
> is a different — and more faithful — model of the implementation.

## Coherence Threshold

VALO separates probabilistic context analysis (Layer 3) from the deterministic safety core (Layer 1). The confidence signal $C$ is compared against a deployment-specific threshold $C_0$. When $C$ falls outside the operational zone $[0.42 \cdot C_0,\ 1.06 \cdot C_0]$, the trigger fires and the formally verified state machine handles the rest.

$C_0 = 4495.27$ is the calibrated threshold for the v1.6 deployment, established from operational telemetry. It is a configured operating parameter, not a universal constant. Different deployments recalibrate $C_0$ from their own telemetry using the same methodology.

The formal guarantee — that once the trigger fires the system provably halts — holds regardless of what value $C_0$ takes. That guarantee is what TLC verifies.

👉 **[Coherence Criterion — methodology and variables](./docs/VALO_COHERENCE_CRITERION.md)**

## Properties Verified

✅ **TypeInvariant** — Type constraints always hold
✅ **NoDeadlock** — System always has a valid next transition or reaches Halt
✅ **HaltIsTerminal** — Once halted, cannot resume
✅ **WORMAppendOnly** — Audit log is immutable (append-only)
✅ **DegradedEventuallyHalt** — Degraded state with timer=0 must reach Halt

## Formal Specification

**Module:** ValoStateMachine
**File:** `ValoStateMachine.tla`
**Configuration:** `ValoStateMachine.cfg`

### State Space

States: {Active, Degraded, Halt, LogFullHalt}

Transitions:
  Active → Active (coherent tick, context_age increments)
  Active → Degraded (coherence/syntax/latency violation)
  Active → Halt (context_age overflow — DirectHalt)
  Degraded → Degraded (timer countdown)
  Degraded → Halt (timer expires)
  Halt → Active (authorized SystemReset — requires 2-person auth)
  Any → LogFullHalt (audit log full — terminal)

### Configuration Constants

The repository's `ValoStateMachine.cfg` uses CI-reduced constants for fast automated
checking. The exhaustive validation reported above (1,662 distinct states) was performed
with the full-scale constants listed here:

| Constant | Full validation | CI config (`ValoStateMachine.cfg`) |
|----------|----------------|------------------------------------|
| MaxDegradedTime | 15 | 5 |
| MaxContextAge | 10 | 3 |
| MaxLogSize | 11 | 5 |

## Proven Guarantees

1. **Safety:** The system maintains type safety across all states
2. **Termination:** From any degraded state, the system eventually halts
3. **Immutability:** Audit log entries cannot be modified or deleted
4. **No Deadlock:** The system never enters an infinite loop or hangs (proven across all 1,662 reachable states of the full-scale model)

## What This Does NOT Prove

❌ **Confidence metric correctness** — We don't verify that confidence < threshold correctly identifies unsafe outputs
❌ **Implementation fidelity** — Code may not match this specification
❌ **False positive/negative rates** — Detection accuracy is unproven
❌ **External data trustworthiness** — Only the logic boundaries are verified

Key distinction: This formal verification proves the state machine logic is correct. It does NOT prove the confidence calculation or detection mechanism are correct.

## Regulatory Compliance

VALO is designed as a technical control supporting compliance with EU AI Act obligations applicable to high-risk AI systems under Annex III. Specifically:

- **Article 12 (Logging):** WORM append-only audit log records every state transition with timestamps and hash-chained integrity
- **Article 14 (Human oversight):** Two-person (MANAGER + OPERATOR) YubiKey-authenticated override; all manual interventions logged before propagation
- **Article 15 (Accuracy, robustness, cybersecurity):** Formally-verified deterministic halt — TLC exhaustively checked every reachable state of the specification (1,662 distinct states at full-scale constants) with zero counterexamples. Verification applies to the TLA+ specification; implementation conformance is established through shared test vectors, not a refinement proof (see "What This Does NOT Prove")

Deployment timeline for stand-alone Annex III systems under the Digital Omnibus agreement: **2 December 2027**.

Key message: We don't claim outputs are always safe. We prove: When you decide to stop, the system provably stops.

## Verification Scope

The TLC model check exhaustively verifies the **state machine logic** in `ValoStateMachine.tla`:
- All reachable states satisfy the type invariants
- Degraded state with timer=0 always leads to Halt or LogFullHalt
- WORM audit log is append-only across all transitions

The following are **explicitly out of scope** of this formal verification:
- Confidence threshold correctness (whether `0.42·c0 ≤ conf ≤ 1.06·c0` correctly identifies unsafe outputs)
- Compiler fidelity (that compiled Rust code matches the TLA+ model)
- Floating-point semantics (edge cases in f64 coherence arithmetic)
- OOD detection (DNNs may be overconfident on out-of-distribution inputs)

## Integrations

### VAIG Sidecar — per-token LLM inference guard

`sidecar/vaig.py` is an HTTP proxy that sits between your application and any OpenAI-compatible LLM API (vLLM, Ollama, OpenAI). Every generated token is evaluated against the L1 Guardian. Tokens that trigger HALT are replaced with `[REDACTED]` and logged to the WORM audit trail.

```bash
python sidecar/vaig.py \
  --upstream http://localhost:11434 \
  --port 8080 \
  --l1-tcp 127.0.0.1:7743 \
  --tau 0.10

# Health check
curl http://localhost:8080/health

# Live token stats
curl http://localhost:8080/v1/status
```

Response headers on every proxied reply:
- `X-Valo-Status: allow | degraded | halt`
- `X-Valo-Confidence: degraded` (only when degraded)

### MCP Server — AI assistant integration

`mcp_server.py` exposes VALO to AI assistants (Claude Desktop, Claude Code, GitHub Copilot) via the Model Context Protocol.

```bash
pip install mcp
python mcp_server.py --l1-tcp 127.0.0.1:7743
```

**Available tools:**

| Tool | Description |
|------|-------------|
| `validate_decision` | Send confidence score to L1 → ALLOW / DEGRADED / HALT |
| `check_coherence` | Check if score is in [0.42·c₀, 1.06·c₀] — no L1 needed |
| `report_status` | Bridge connection state, last decision, frames sent |
| `evaluate_prompt` | Convenience: confidence + action label → full evaluation |
| `process_permit` | Verify a signed RACS permit and run it through the golden execution path |

**Claude Desktop `claude_desktop_config.json`:**
```json
{
  "mcpServers": {
    "valo-v5": {
      "command": "python",
      "args": ["/path/to/valo-v5-core/mcp_server.py", "--l1-tcp", "127.0.0.1:7743"]
    }
  }
}
```

## Next Steps

- [ ] UiS Academic Validation (target: July 31, 2026)
- [ ] Operator Pilots (Net Zero Compute / NetZero)
- [ ] Post-Deployment Certification (post-pilot; applicable deadline 2 December 2027)

---

**Verified by:** TLC Model Checker
**Repository:** https://github.com/Valo-Research-Geoup/valo-v5-core
**Specification Path:** `formal-verification/ValoStateMachine.tla`
