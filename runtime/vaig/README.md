# VAIG — REHT Authority & Integrity Gateway

Governance runtime for agentic AI systems. Apache 2.0.

VAIG is the runtime governance layer in the REHT architecture.

REHT defines admissibility semantics.  
VAIG evaluates runtime governance conditions.  
BARO provides interpreted observations.  
Speider collects and normalizes source material.  
RACS defines message and receipt contracts.  
REHT V5 Core enforces bounded execution-state transitions.

VAIG sits architecturally outside the model it governs. It is not a model feature, prompt convention or soft guardrail.

## Core thesis

AI risk does not arise only when a model produces an output. The critical risk appears when an AI-mediated output changes what can happen next.

VAIG governs the bounded transition from represented evidence to governed execution or refusal.

## Governance path

```text
Evidence -> EvidenceCondition -> Intent -> Authorization -> Action / Refusal -> Resolution -> Accountability Thread -> Receipt
```

Reality is an external dependency. Evidence enters VAIG only as a represented condition. Human approval, override and organizational responsibility are external authority inputs expressed through explicit interfaces.

## Hard boundary

VAIG governs:

- EvidenceCondition
- intent admissibility checks
- authorization inputs
- execution or refusal routing
- resolution handoff
- accountability thread
- receipt production

VAIG does not govern:

- truth itself
- morality
- human standing
- organizational legitimacy
- organizational responsibility
- long-term social continuity

Those remain external governance contexts.

## Core invariant

```text
No intent may form unless EvidenceCondition is VALIDATED or OVERRIDDEN.
```

This is a pre-intent governance rule, not a truth claim.

## Runtime inference layer

```text
User prompt + model response -> Scout -> Dirigent -> Ensemble -> AARM decision -> hash-chained log
```

AARM decisions:

- ALLOW
- MODIFY
- DEFER
- DENY
- STEP_UP
- HALT

## Epistemic underdetermination

VAIG treats `UNDERDETERMINED` as a first-class evidence state when current evidence cannot legitimately select one surviving explanation or revision path.

The canonical contract preserves alternatives, auxiliary assumptions and discriminating tests. It never grants execution authority. When alternatives imply different consequences, the case requires human review or new evidence before consequential execution. See `docs/epistemic-underdetermination.md`.

## Analytic tradecraft gate

VAIG can apply a deterministic structured-analysis gate before consequential use of represented evidence.

The gate checks:

- provenance and evidence integrity
- independent corroboration and influence risk
- explicit key assumptions
- ACH-style support and contradiction mapping
- missing expected observations
- whether one hypothesis is uniquely least contradicted

Outputs are `SUFFICIENT`, `CONSTRAINED` or `INSUFFICIENT`. `INSUFFICIENT` blocks consequential action. `CONSTRAINED` requires human review. The gate never grants execution authority and all consequential action still requires REHT clearance. See `docs/analytic-tradecraft-gap-analysis.md`.

## Deployment modes

VAIG can be deployed as:

- Wrapper
- Proxy
- Sidecar
- MCP service
- REHT V5 Core bridge

Deployment modes must not own independent governance semantics. Adapters call shared VAIG logic and render, forward or enforce the result.

## RACS boundary

RACS standardizes envelopes, states and receipts exchanged between components. RACS does not decide admissibility and does not execute actions.

## Claim boundary

Allowed:

- VAIG is a testable runtime governance stack for agentic AI.
- VAIG contains a pre-intent evidence gate.
- VAIG produces explicit decisions and traceable receipts.
- VAIG can be tested in one bounded workflow.

Not allowed:

- VAIG is fully production-certified.
- VAIG guarantees regulatory compliance.
- VAIG guarantees insurance acceptance.
- RACS is already an adopted market standard.
- BARO predicts crises.

## Provenance

Active VAIG architecture is defined independently in this repository. Earlier collaboration-linked material is preserved only in historical or provenance records and is not an active runtime dependency.

See `docs/ip/CHARLES_RUPP_TRACE_REGISTER.md`.

## Status

Architecture and pilot-stage implementation. Hardening remains required before production use.

## Edge / on-device modules (vaig.vaig_embedded)

`vaig.vaig_embedded` is an edge-oriented reference runtime: stdlib-only,
network-free, hardware-probing (`LiteEnsemble` five-instrument scoring,
`SQLiteWORM` on-device log, `VUMeter`, `hardware_detect`). It is a Python
reference implementation and is NOT accelerator-backed; production edge
deploys should target Rust/C/TFLite/NPU with the same five-instrument
contract. A per-token latency test enforces the <1ms edge budget.

## Anti-coercion modules (vaig.swarm)

`vaig.swarm` restores the anti-coercion / kidnapping-resistance prototype
preserved from valo-platform (duress codes, time-lock, Shamir threshold,
revocation). STATUS: CONCEPT / NOT-AUDITED — `RingSignature` and `VRF` are
reference constructions, not audited cryptography; replace with a reviewed
library before any real security use.

## License

Apache 2.0 — VALO Research Group AS
