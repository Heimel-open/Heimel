# VAIG Roadmap

Current release has expanded from runtime inference governance into a broader governance stack:

```text
Reality -> Evidence -> EvidenceCondition -> Intent -> Authorization -> Action/Refusal -> RRP -> Accountability Thread -> Receipt
```

The original L1-L8 runtime stack remains valid, but it now sits inside a wider pre-intent and post-refusal governance model.

---

## Track 1 — Open Source (this repo)

| Version | What |
|---|---|
| v0.2 (released) | L1-L5: ensemble scoring, AARM, WORM log |
| v0.3 | L5.5-L8 + semantic drift + `vaig_core/` canonical types |
| v0.4 | RRP: Refusal Resolution Protocol, Accountability Thread, refusal-to-action lifecycle |
| v0.5 | EvidenceCondition: pre-intent admissibility gate + IntentFactory enforcement + Receipt chain-of-custody |
| v0.6 | Schema validation and cross-mode invariants across Proxy, Sidecar and MCP |
| v0.7 | Demo flow: Evidence -> Intent -> VAIG -> Refusal/Action -> Receipt |

---

## v0.5 — Pre-Intent Governance

The major architectural change is upstream governance before authorization.

Previous simplified model:

```text
Intent -> Authorization -> Execution
```

New model:

```text
Reality
-> Evidence
-> EvidenceCondition
-> Intent
-> VAIG Authorization
-> Action / Refusal
-> RRP
-> Accountability Thread
-> Receipt
```

### Core invariant

```text
No intent may form unless EvidenceCondition is VALIDATED or OVERRIDDEN.
```

Admissible:

```text
VALIDATED
OVERRIDDEN
```

Blocked:

```text
SUBMITTED
STALE
CONTESTED
INSUFFICIENT
```

### What this adds

| Component | What |
|---|---|
| `EvidenceCondition` | Captures evidential admissibility before intent formation |
| `IntentFactory` | Blocks intent formation unless evidence is admissible |
| `Receipt` | Binds evidence, intent, VAIG outcome, RRP thread and final status |
| RRP tests | Validate lifecycle, evidence scenarios and receipts |

---

## v0.3 — Existing Runtime Governance Stack

| Component | Layer | What |
|---|---|---|
| `vaig_core/` | Core | Canonical type package: DistrustLevel, GateStatus, PolicyConfig, AuditReceipt, WORMLog |
| `RecoveryManager` | L5.5 | Structured escalation after L4 HALT: RETRY -> FALLBACK -> SANDBOX -> ISOLATE -> HUMAN_STOP |
| `CouncilQueue` + Flask API | L6 | Async human review queue for L3/L4 decisions |
| `Skjaersilden` | L6.5 | Council verdict -> domain threshold calibration |
| `CAKM` | L7 | Cross-session distrust pattern tracking |
| `DeltaBoxSandbox` | L8 | Checkpoint + rollback for agentic execution |
| `proxy/semantic.py` | Instrument 4 | Semantic drift detection |

---

## Track 2 — Enterprise (VALO, private)

Enterprise builds on the open source track and hardens it for regulated/high-risk deployments.

| Component | What |
|---|---|
| DeterministicGate | HMAC-signed permit/deny per state transition |
| TLA+ specification | Formal verification of gate + rollback invariants |
| Council -> DeterministicGate | Blocking Council for high-risk continuation |
| Redis-backed CAKM | Multi-instance persistent distrust memory |
| EvidenceCondition registry | Persistent evidence admissibility store |
| Receipt export | Regulator-facing chain-of-custody export |

---

## Track 3 — Crypto / On-chain governance

| Component | What |
|---|---|
| On-chain WORM receipts | Each decision hash anchored to public chain |
| Smart contract governance rules | Threshold changes require multi-sig |
| Distributed Council (BFT) | Independent quorum for Council decisions |
| ZK threshold proofs | Proof of scoring against published thresholds without revealing content |
| Evidence attestation anchoring | Optional anchoring of EvidenceCondition receipts |

---

## Deployment modes

Proxy, Sidecar, MCP and Wrapper are not separate governance models.

They are deployment modes around one shared VAIG Core.

```text
Wrapper -> low-friction embedding
Proxy   -> transparent HTTP gateway
Sidecar -> stateful enterprise runtime
MCP     -> tool interface for AI assistants
L1      -> high-assurance verified guardian bridge
```

The governance model must remain shared:

```text
same governance input -> same governance decision
```

---

## Convergence point

Previous convergence point:

```text
score -> gate -> rollback -> Council -> on-chain receipt
```

Updated convergence point:

```text
evidence -> intent -> authorization -> execution/refusal -> RRP -> receipt
```

Without EvidenceCondition, VAIG can prove that an action was authorized.

With EvidenceCondition, VAIG can also prove that the intent was formed from admissible evidence.

---

## What is NOT on this roadmap

- Online WeightLearner as live threshold mutation
- Shadow Council as background parallel scoring without clear decision rights
- Public TLA+ production spec before independent audit
- Adapter-specific policy engines in Proxy, Sidecar or MCP
- Governance semantics hidden inside deployment adapters
