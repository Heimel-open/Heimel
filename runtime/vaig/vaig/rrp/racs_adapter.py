"""VAIG → RACS adapter.

Mapping:
  APPROVE  -> ALLOW
  RESCOPE  -> MODIFY
  REJECT   -> DENY
  ESCALATE -> STEP_UP
  TERMINATE-> HALT

Policy:
- Fail-closed on None/unknown AuthorityDecision -> DENY.
- No execution authority; adapter returns structured GovernanceResult-compatible data.
- Preserves source decision, evidence, uncertainty, rationale in metadata.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from vaig.rrp.core import (
    AuthorityAssignment,
    AuthorityDecision,
    RefusalEvent,
    SeverityLevel,
)
from vaig.rrp.evidence import ConfidenceLevel, EvidenceCondition
from vaig.rrp.intent import Intent


RACS_DECISION_MAP: Dict[AuthorityDecision, str] = {
    AuthorityDecision.APPROVE: "ALLOW",
    AuthorityDecision.RESCOPE: "MODIFY",
    AuthorityDecision.REJECT: "DENY",
    AuthorityDecision.ESCALATE: "STEP_UP",
    AuthorityDecision.TERMINATE: "HALT",
}


def _digest(value: object) -> str:
    return hashlib.sha256(str(value).encode()).hexdigest()


def map_authority_decision_to_racs(
    authority_decision: Optional[AuthorityDecision],
) -> str:
    """Fail-closed: unknown or None -> DENY."""
    if authority_decision is None:
        return "DENY"
    try:
        return RACS_DECISION_MAP[authority_decision]
    except KeyError:
        return "DENY"


@dataclass(frozen=True)
class RacsAdapterResult:
    decision: str
    reasons: Tuple[str, ...]
    request_digest: str
    tenant_id: str = "unknown"
    # Preserved source context
    source_authority_decision: Optional[str] = None
    evidence_condition_id: Optional[str] = None
    confidence_level: Optional[float] = None
    intent_action_type: Optional[str] = None
    refusal_id: Optional[str] = None
    adapter_version: str = "vaig-rrp-v1"


def build_governance_result(
    authority_decision: Optional[AuthorityDecision],
    *,
    refusal_event: Optional[RefusalEvent] = None,
    evidence_condition: Optional[EvidenceCondition] = None,
    confidence_level: Optional[ConfidenceLevel] = None,
    severity_level: Optional[SeverityLevel] = None,
    intent: Optional[Intent] = None,
    tenant_id: str = "unknown",
    request_digest: Optional[str] = None,
    authority_assignment: Optional[AuthorityAssignment] = None,
) -> RacsAdapterResult:
    """Build RACS-compatible result from VAIG evidence and authority state.

    All inputs are observational only; this function never executes or
    authorizes changes.
    """
    decision = map_authority_decision_to_racs(authority_decision)

    reasons: list[str] = []
    if severity_level is not None:
        reasons.append(f"SEVERITY_{severity_level.value.upper()}")
    if confidence_level is not None:
        reasons.append(f"CONFIDENCE_{confidence_level.name.upper()}")
    if evidence_condition is not None:
        reasons.append(f"EVIDENCE_STATUS_{evidence_condition.validation_status.upper()}")
        reasons.append(f"EVIDENCE_ID_{evidence_condition.evidence_id}")
    if refusal_event is not None:
        reasons.append(f"REFUSAL_CATEGORY_{refusal_event.category.value.upper()}")
        reasons.append(f"REFUSAL_ID_{refusal_event.refusal_id}")
        reasons.append(f"TRIGGERED_RULE_{refusal_event.triggered_rule}")
    if intent is not None:
        reasons.append(f"INTENT_ACTION_{intent.action_type}")
    if authority_assignment is not None:
        reasons.append(f"AUTHORITY_ROLE_{authority_assignment.authority_role}")

    return RacsAdapterResult(
        decision=decision,
        reasons=tuple(reasons),
        request_digest=request_digest or _digest(authority_decision),
        tenant_id=tenant_id,
        source_authority_decision=(
            authority_decision.value.upper() if authority_decision else None
        ),
        evidence_condition_id=(
            evidence_condition.evidence_id if evidence_condition else None
        ),
        confidence_level=confidence_level.value if confidence_level else None,
        intent_action_type=intent.action_type if intent else None,
        refusal_id=refusal_event.refusal_id if refusal_event else None,
    )
