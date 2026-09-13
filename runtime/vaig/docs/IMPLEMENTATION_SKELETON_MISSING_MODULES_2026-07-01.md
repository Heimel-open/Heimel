# Implementation Skeleton — Missing VAIG / GEA Modules

Date: 2026-07-01  
Status: engineering skeleton  
Scope: VAIG / GEA / TAD / AGR / PNR / SOL / PERT / Emergency Mode / BARO / NJAL

This document turns the current architecture notes into a buildable implementation plan.

It does not replace `SYSTEM_MAP.md`, `TEST_EVIDENCE.md`, or the existing RRP/VACS implementation.

## 0. Current implemented base

Already present in repository:

- EvidenceCondition
- IntentFactory
- RiskContract
- RRP refusal lifecycle
- Receipt object
- WORMLog hash-chain audit log
- ACS packet schema
- ACS receipt schema
- VACS profile
- ExecutionHandoffAdapter

These form the current minimum runtime base:

```text
EvidenceCondition
→ IntentFactory
→ RiskContract / policy
→ AARM decision
→ Execution handoff OR RRP refusal
→ Receipt / WORM
```

## 1. Missing module map

| Module | Purpose | Build status | First artifact |
|---|---|---|---|
| State Admissibility | Validate whether represented reality is admissible before governance | missing | `src/vaig/gea/state_admissibility.py` |
| TAD / Validity Contract | Determine whether prior authorization remains valid | missing | `src/vaig/gea/tad.py` |
| Continuous Integrity | Detect relevant changes during execution | missing | `src/vaig/gea/continuous_integrity.py` |
| AGR | Route actions to fast / standard / full governance | missing | `src/vaig/gea/agr.py` |
| PNR | Manage safe abort vs atomic completion | missing | `src/vaig/gea/pnr.py` |
| SOL | Select best admissible action with recoverability | missing | `src/vaig/gea/sol.py` |
| PERT | Reconcile authorized intent against actual outcome | missing | `src/vaig/gea/pert.py` |
| Emergency Governance Profile | Governed emergency mode, not bypass | missing | `src/vaig/gea/emergency.py` |
| BARO Adapter | Feed observation/evidence/risk pressure into VAIG | missing | `src/vaig/gea/baro_adapter.py` |
| NJAL Proof Chain | Unified proof/receipt layer across modules | missing | `src/vaig/gea/njal.py` |
| End-to-end demo | Prove action path | missing | `examples/gea_demo.py` |

## 2. Package layout

Create:

```text
src/vaig/gea/
├── __init__.py
├── types.py
├── state_admissibility.py
├── tad.py
├── continuous_integrity.py
├── agr.py
├── pnr.py
├── sol.py
├── pert.py
├── emergency.py
├── baro_adapter.py
└── njal.py

examples/
└── gea_demo.py

tests/gea/
├── test_state_admissibility.py
├── test_tad.py
├── test_continuous_integrity.py
├── test_agr.py
├── test_pnr.py
├── test_sol.py
├── test_pert.py
├── test_emergency.py
└── test_gea_demo.py
```

## 3. Shared types

File:

```text
src/vaig/gea/types.py
```

Minimum objects:

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class GovernanceDecision(str, Enum):
    ALLOW = "ALLOW"
    MODIFY = "MODIFY"
    DEFER = "DEFER"
    DENY = "DENY"
    STEP_UP = "STEP_UP"
    HALT = "HALT"


class GovernanceRoute(str, Enum):
    FAST_PATH = "FAST_PATH"
    STANDARD_VALIDATION = "STANDARD_VALIDATION"
    FULL_GOVERNANCE = "FULL_GOVERNANCE"
    EMERGENCY_MODE = "EMERGENCY_MODE"


class RiskClass(str, Enum):
    A = "A"
    B = "B"
    C = "C"


@dataclass
class GovernanceContext:
    context_id: str
    state_hash: str
    policy_hash: str
    authority_hash: str
    evidence_hash: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CandidateAction:
    action_id: str
    action_type: str
    target: str
    expected_outcome: str
    risk_class: RiskClass
    reversible: bool
    irreversible: bool
    compensation_available: bool
    escalation_rule: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

## 4. State Admissibility

Question:

```text
Is the represented reality valid enough for governance to proceed?
```

File:

```text
src/vaig/gea/state_admissibility.py
```

Minimum API:

```python
@dataclass
class StateAdmissibilityResult:
    admissible: bool
    reason: str
    state_hash: str
    evidence_refs: list[str]


class StateAdmissibilityGate:
    def evaluate(self, context: GovernanceContext) -> StateAdmissibilityResult:
        ...
```

Initial rules:

- missing state hash -> not admissible
- missing evidence hash -> not admissible
- stale observation -> not admissible
- contested observation -> STEP_UP / not admissible
- validated or overridden evidence -> admissible

First tests:

- valid state passes
- missing evidence blocks
- stale context blocks
- overridden evidence passes but marks override

## 5. TAD / Validity Contract

Question:

```text
Is the prior governance decision still valid at the moment of consequence?
```

File:

```text
src/vaig/gea/tad.py
```

Minimum API:

```python
@dataclass
class ValidityContract:
    contract_id: str
    issued_at: str
    valid_until: str
    context_hash: str
    policy_hash: str
    authority_hash: str
    action_id: str


@dataclass
class TADResult:
    valid: bool
    reason: str
    invalidation_event: Optional[str] = None


class TADGate:
    def evaluate(self, contract: ValidityContract, context: GovernanceContext) -> TADResult:
        ...
```

Invalidation events:

- expired horizon
- context hash changed
- policy hash changed
- authority hash changed
- BARO escalation
- Continuous Integrity failure
- PERT deviation

Core rule:

```text
TAD is not a timer. It is a validity contract.
```

## 6. Continuous Integrity

Question:

```text
Has anything relevant changed while the action is pending or executing?
```

File:

```text
src/vaig/gea/continuous_integrity.py
```

Minimum API:

```python
@dataclass
class IntegritySignal:
    signal_id: str
    signal_type: str
    severity: str
    source: str
    metadata: dict


@dataclass
class IntegrityResult:
    intact: bool
    reason: str
    signals: list[IntegritySignal]


class ContinuousIntegrityMonitor:
    def evaluate(self, signals: list[IntegritySignal]) -> IntegrityResult:
        ...
```

Initial rule:

- any critical signal -> not intact
- policy/authority/context change -> not intact
- warning signal -> STEP_UP candidate

## 7. AGR — Adaptive Governance Router

Question:

```text
Which governance route is valid now?
```

File:

```text
src/vaig/gea/agr.py
```

Minimum API:

```python
@dataclass
class AGRInput:
    action: CandidateAction
    state_admissible: bool
    tad_valid: bool
    integrity_intact: bool
    coherence_class: str
    emergency_active: bool = False


@dataclass
class AGRResult:
    route: GovernanceRoute
    reason: str


class AdaptiveGovernanceRouter:
    def route(self, data: AGRInput) -> AGRResult:
        ...
```

Routing rules:

```text
Emergency active -> EMERGENCY_MODE
State invalid -> FULL_GOVERNANCE / STEP_UP
TAD invalid -> FULL_GOVERNANCE
Integrity failed -> FULL_GOVERNANCE or HALT
Risk A + TAD valid + high coherence -> FAST_PATH
Risk B + stable context -> STANDARD_VALIDATION
Risk C -> FULL_GOVERNANCE
```

## 8. PNR — Irreversibility Boundary

Question:

```text
Can the action still be safely interrupted?
```

File:

```text
src/vaig/gea/pnr.py
```

Minimum API:

```python
@dataclass
class ExecutionProgress:
    action_id: str
    pnr_reached: bool
    completion_percent: float
    metadata: dict


@dataclass
class InterruptDecision:
    abort_allowed: bool
    atomic_completion_required: bool
    lock_after_completion: bool
    reason: str


class IrreversibilityBoundary:
    def evaluate_interrupt(self, progress: ExecutionProgress) -> InterruptDecision:
        ...
```

Rules:

```text
Before PNR -> safe abort
After PNR -> atomic completion + lock + PERT + human review
```

## 9. SOL — Recoverability Optimizer

Question:

```text
Which admissible action preserves governability if it is wrong?
```

File:

```text
src/vaig/gea/sol.py
```

Minimum API:

```python
@dataclass
class SOLResult:
    selected_action: Optional[CandidateAction]
    rejected_actions: list[str]
    step_up_actions: list[str]
    reason: str


class RecoverabilityOptimizer:
    def filter_admissible(self, actions: list[CandidateAction]) -> tuple[list[CandidateAction], list[str], list[str]]:
        ...

    def select(self, actions: list[CandidateAction]) -> SOLResult:
        ...
```

Hard rule:

```text
Irreversible + no verified compensation + no escalation rule -> not admissible
```

Principle:

```text
Recoverability outranks expected correctness when consequences are irreversible.
```

## 10. PERT — Post-Execution Reconciliation

Question:

```text
Did the actual outcome match the authorized intent?
```

File:

```text
src/vaig/gea/pert.py
```

Minimum API:

```python
@dataclass
class ExecutionOutcome:
    action_id: str
    actual_outcome: str
    outcome_hash: str
    metadata: dict


@dataclass
class PERTResult:
    conformance: bool
    reason: str
    requires_policy_feedback: bool
    requires_human_review: bool


class PostExecutionReconciler:
    def reconcile(self, intent_expected: str, outcome: ExecutionOutcome) -> PERTResult:
        ...
```

States:

- Verified Conformance
- Outcome Deviation
- Compensation Required
- Human Review Required

Avoid language:

- self-learning
- autonomous policy update
- trust score

Use:

- execution integrity
- verified conformance
- controlled policy evolution

## 11. Emergency Governance Profile

Question:

```text
Is this a valid governed emergency mode?
```

File:

```text
src/vaig/gea/emergency.py
```

Minimum API:

```python
@dataclass
class EmergencyGovernanceProfile:
    profile_id: str
    allowed_actions: list[str]
    validity_seconds: float
    required_sensor_sources: int
    required_model_confirmation: bool
    requires_operator_notification: bool


@dataclass
class EmergencyAssessment:
    active: bool
    reason: str
    profile_id: Optional[str] = None


class EmergencyMandateGate:
    def evaluate(self, action: CandidateAction, profile: EmergencyGovernanceProfile, context: GovernanceContext) -> EmergencyAssessment:
        ...
```

Principle:

```text
Emergency is not an exception to governance.
It is a governed execution mode with stricter admissibility requirements.
```

Rules:

- emergency action must be in profile
- emergency has its own Validity Horizon
- sensor + model confirmation required
- after execution -> PERT mandatory
- after PNR -> atomic completion, lock, review

## 12. BARO Adapter

Question:

```text
What observation/evidence/risk pressure should enter VAIG?
```

File:

```text
src/vaig/gea/baro_adapter.py
```

Minimum API:

```python
@dataclass
class BAROSignal:
    signal_id: str
    source: str
    signal_type: str
    confidence: float
    risk_pressure: str
    evidence_hash: str
    metadata: dict


class BAROEvidenceAdapter:
    def to_evidence_condition_input(self, signal: BAROSignal) -> dict:
        ...
```

Boundary:

```text
BARO observes.
VAIG governs.
BARO cannot authorize execution.
```

## 13. NJAL Proof Chain

Question:

```text
Can the full decision chain be proven?
```

File:

```text
src/vaig/gea/njal.py
```

Minimum API:

```python
@dataclass
class NJALProof:
    proof_id: str
    action_id: str
    evidence_hash: str
    context_hash: str
    policy_hash: str
    decision: str
    outcome_hash: Optional[str]
    receipt_hash: str


class NJALProofChain:
    def create_proof(self, **kwargs) -> NJALProof:
        ...

    def append_to_worm(self, proof: NJALProof) -> str:
        ...
```

Purpose:

- unify receipt, WORM and PERT result
- preserve non-repudiation
- support audit/review

## 14. End-to-end demo

File:

```text
examples/gea_demo.py
```

Demo path:

```text
ACS packet
→ BARO signal / evidence input
→ EvidenceCondition
→ State Admissibility
→ IntentFactory
→ TAD contract
→ AGR route
→ SOL select
→ ExecutionHandoffAdapter
→ PNR check
→ ACT mock execution
→ PERT reconciliation
→ NJAL proof
→ WORM receipt
```

Demo scenarios:

1. Allowed reversible action.
2. Blocked stale evidence.
3. Fast path valid TAD contract.
4. TAD invalidation -> full validation.
5. Irreversible no compensation -> STEP_UP.
6. Emergency mode valid -> execute within profile.
7. Emergency mode invalid -> HALT.
8. Outcome mismatch -> PERT human review.

## 15. Build order

Do not build everything at once.

Build in this order:

1. `types.py`
2. `state_admissibility.py`
3. `tad.py`
4. `agr.py`
5. `pnr.py`
6. `sol.py`
7. `pert.py`
8. `emergency.py`
9. `baro_adapter.py`
10. `njal.py`
11. `examples/gea_demo.py`

## 16. First milestone

Target:

```text
One action goes through the full governed path and produces a receipt.
```

Success condition:

- action with valid evidence -> ALLOW -> mock execute -> PERT conformance -> NJAL proof
- action with stale evidence -> blocked before intent
- irreversible action without compensation -> STEP_UP
- TAD invalidation -> full governance

## 17. Claims allowed after first milestone

Allowed:

- VAIG has a demonstrable execution-boundary path.
- GEA modules exist as implementation skeletons.
- State Admissibility, TAD, AGR, PNR, SOL and PERT can be tested in a mock workflow.
- Receipts can be produced for governed execution and refusal.

Not allowed:

- production readiness
- formal certification
- real-time latency guarantee
- standards adoption
- autonomous legal compliance
