from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


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
