# Test Evidence and Readiness Map

Status: verified against `main` at `5c350e29f6d079308c6b35d158bc57190c079869`
Scope: evidence of what is implemented, tested, draft-only or deferred

This file prevents claims from exceeding the current repo evidence.

## 1. Claim discipline

Use only claims that can be traced to code, tests, schemas or controlled documents.

Do not claim:

- enterprise certification
- regulatory approval
- insurance acceptance
- full production hardening
- complete standardization
- complete formal verification inside this repo

Use safer language:

- testable runtime governance stack
- pre-intent evidence gate implemented in code
- refusal lifecycle implemented in code
- ACS packet and receipt schemas present
- WORM / receipt direction present
- EU submission framing drafted
- pilot-ready core, not finished enterprise product

## 2. Invariants to protect

| Invariant | Evidence location | Readiness |
|---|---|---|
| Intent cannot form unless EvidenceCondition is VALIDATED or OVERRIDDEN | `vaig/rrp/intent.py`, `vaig/rrp/evidence.py` | implemented, tested |
| Evidence validation is contract execution, not model inference | `vaig/rrp/evidence.py`, `vaig/rrp/risk_contract.py` | implemented, tested |
| Cross-domain intent can be blocked across isolated domains | `vaig/rrp/intent.py`, `vaig/rrp/risk_contract.py` | implemented, tested |
| Refusal has a lifecycle, not only a terminal denial | `vaig/rrp/core.py` | implemented, tested |
| Accountability thread records state changes | `vaig/rrp/core.py` | implemented, tested |
| Receipt binds evidence, intent, outcome, refusal, authority and thread | `vaig/rrp/receipt.py` | implemented, tested |
| WORM log is SHA-256 hash-chained and tamper-evident | `vaig/worm.py`, `tests/test_worm.py` | implemented, tested — see `docs/worm-audit-guarantees.md` |
| Gate boundary is deterministic; cost-value governs whether a call is worth executing | `vaig/agent_loop/risk_engine.py` | implemented, tested |
| Context rebilling multiplier is computed before model call | `vaig/economy/token_meter.py` | implemented, tested |
| High-consequence tasks are never downgraded for cost | `vaig/economy/router.py` | implemented, tested |
| ACS packet has required intent/evidence/risk/policy/decision fields | `vacs/schema/acs_packet.schema.json` | schema present |
| ACS receipt has action/input/policy hashes and decision | `vacs/schema/acs_receipt.schema.json` | schema present |
| Unknown authority levels fail closed | `vaig/agent_loop/risk_engine.py`, `why/unknown_fallback.py`, `tests/test_unknown_fallback.py` | implemented and directly tested; portfolio-wide wiring not proven |
| WHY Gate evaluates justification continuity without owning execution enforcement | `vaig/why_gate.py`, `tests/test_why_gate_runtime.py` | runtime implemented and tested |
| CAN/SHOULD/WHY aggregate as weakest link; PURPLE overrides all | `vaig/management_overlay/signals/can_should_why.py` | implemented, tested |
| PURPLE disables consequence commitment; action risk separate from system trust | `vaig/management_overlay/api/status.py` | implemented, tested |

## 3. Known test areas (current: 766 passing, 2026-08-05)

Verified test families with current run evidence:

| Test file | Count | Scope |
|---|---|---|
| `test_rrp_lifecycle.py` | — | RRP state machine transitions |
| `test_rrp_receipts.py` | — | Receipt binding and hash |
| `test_evidence_condition.py` | — | EvidenceCondition lifecycle |
| `test_risk_contract.py` | — | Domain rules and blocking |
| `test_rrp_governance_scenarios.py` | — | End-to-end governance flows |
| `test_agent_loop_authority.py` | — | Authority scope gate |
| `test_agent_loop_drift.py` | — | Semantic drift threshold |
| `test_agent_loop_observation.py` | — | Observation trust gate |
| `test_agent_loop_human_transfer.py` | — | Human transfer receipt |
| `test_agent_loop_cost_value.py` | — | Cost-value gate (downshift/reduce/stop) |
| `test_authority_gate.py` | — | Delegation, expiry, step-up, halt |
| `test_value_meter.py` | — | Authorized Value / GateWeight / ControlYield |
| `test_context_rebilling.py` | — | Rebilling multiplier formula (10.5x at 20 turns) |
| `test_language_multiplier.py` | — | Language inflation factor composition |
| `test_model_routing.py` | — | Model tier routing rules |
| `test_cost_value_gate.py` | — | Economy gate: compress/retrieve/stop/require_human |
| `test_why_gate_runtime.py` | — | WHY Gate v2: 4-dimension score, hash chain |
| `test_worm.py` | — | WORM hash-chain construction and verify() |
| `test_management_overlay.py` | — | CAN/SHOULD/WHY aggregation, PURPLE override, display formats |
| `test_evidence_intake.py` | — | Versioned evidence-package and workflow bindings |
| `test_aggregation.py`, `test_aggregation_p02.py` | — | Policy-driven aggregation, veto and abstention behavior |
| `test_analytic_tradecraft.py` | — | Structured analytic tradecraft assessment |
| `test_epistemic_underdetermination.py` | — | Alternative-hypothesis and underdetermination handling |
| `test_reflective_inquiry.py` | — | Reflective inquiry outcomes and referrals |
| `test_instruments.py` and instrument-specific suites | — | Instrument result contracts and containment signals |
| `test_version.py` | — | Public runtime version uses the canonical source |

## 4. Current verification pass

```
Date: 2026-08-05
Command: python -m pytest -q
Result: 766 passed, 0 failed, 0 errors (26 DeprecationWarnings)
Python: 3.12.3
Branch: main (after agent-loop AARM wiring and dead-module removal)
```

Interpretation: all collected tests are green against the installed wheel and repository test corpus. Distributed deployment, hardware-backed or production WORM, external enforcement, on-chain receipts, ZK proofs and regulatory conformity are not established by this run.

## 5. Draft-only or deferred items

Treat these as not production claims until verified:

- Purple out-of-band monitoring
- SSIP schema unification
- portfolio-wide unknown-fallback integration
- WORM read API for why attribution
- AARM logging integration for `should` explanation
- public TLA+ production spec
- enterprise DeterministicGate
- on-chain WORM receipts
- ZK threshold proofs
- distributed Council

## 6. Readiness categories

Use this language:

### Implemented

Code or schema exists and can be inspected.

### Tested

There is a direct test and current run evidence.

### Draft

Specification exists but is not wired or not production behavior.

### Roadmap

Planned or described, not implemented.

### Reserved

Kept private or withheld until submission / paper / partner agreement.

## 7. Pilot claim

Allowed pilot claim:

VAIG has a testable core for runtime governance, evidence-bound intent, structured refusal and receipt generation.

Not allowed:

VAIG is fully production-certified for regulated enterprise deployment.

## 8. Audit claim

Allowed audit claim:

The architecture is designed to produce structured receipts and tamper-evident audit evidence.

Not allowed:

The system guarantees legal compliance or insurance acceptance.

## 9. Completed — current test run recorded in section 4

See section 4 for the 2026-08-05 verification pass (766 passed).

Detailed run evidence: `docs/test_runs/2026-07-31-vaig-core.md`
