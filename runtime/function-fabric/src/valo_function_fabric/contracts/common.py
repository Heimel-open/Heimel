from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import Enum
from hashlib import sha256
from typing import Any

SCHEMA_VERSION = "v1"


def utcnow() -> datetime:
    return datetime.now(UTC)


def canonical_digest(value: Any) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    ).encode()
    return sha256(raw).hexdigest()


class RiskClass(str, Enum):
    R0_INFORMATIONAL = "R0_INFORMATIONAL"
    R1_REVERSIBLE_ADMINISTRATIVE = "R1_REVERSIBLE_ADMINISTRATIVE"
    R2_OPERATIONAL = "R2_OPERATIONAL"
    R3_FINANCIAL_LEGAL = "R3_FINANCIAL_LEGAL"
    R4_RIGHTS_IMPACTING = "R4_RIGHTS_IMPACTING"
    R5_SAFETY_CRITICAL = "R5_SAFETY_CRITICAL"


RISK_ORDER = {
    RiskClass.R0_INFORMATIONAL: 0,
    RiskClass.R1_REVERSIBLE_ADMINISTRATIVE: 1,
    RiskClass.R2_OPERATIONAL: 2,
    RiskClass.R3_FINANCIAL_LEGAL: 3,
    RiskClass.R4_RIGHTS_IMPACTING: 4,
    RiskClass.R5_SAFETY_CRITICAL: 5,
}


class AutonomyLevel(str, Enum):
    HUMAN = "HUMAN"
    OBSERVE = "OBSERVE"
    DRAFT = "DRAFT"
    RECOMMEND = "RECOMMEND"
    STEP_UP = "STEP_UP"
    AUTO_EXECUTE = "AUTO_EXECUTE"


AUTONOMY_ORDER = {
    AutonomyLevel.HUMAN: 0,
    AutonomyLevel.OBSERVE: 1,
    AutonomyLevel.DRAFT: 2,
    AutonomyLevel.RECOMMEND: 3,
    AutonomyLevel.STEP_UP: 4,
    AutonomyLevel.AUTO_EXECUTE: 5,
}


class IdempotencyRequirement(str, Enum):
    NONE = "NONE"
    REQUIRED = "REQUIRED"
    VERIFY_BEFORE_REPLAY = "VERIFY_BEFORE_REPLAY"


class FunctionStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"


class GovernanceChange(str, Enum):
    NONE = "NONE"
    INPUT_CHANGED = "INPUT_CHANGED"
    OUTPUT_CHANGED = "OUTPUT_CHANGED"
    EFFECTS_INCREASED = "EFFECTS_INCREASED"
    RISK_CHANGED = "RISK_CHANGED"
    AUTHORITY_WEAKENED = "AUTHORITY_WEAKENED"
    EVIDENCE_WEAKENED = "EVIDENCE_WEAKENED"
    AUTONOMY_EXPANDED = "AUTONOMY_EXPANDED"
    BREAKING_GOVERNANCE_CHANGE = "BREAKING_GOVERNANCE_CHANGE"
