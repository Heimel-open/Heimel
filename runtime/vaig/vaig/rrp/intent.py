"""
Intent — Evidence-bound intent with domain segmentation.

Structural invariants:
- Intent cannot form unless EvidenceCondition is admissible.
- Cross-domain intent across isolated domains is blocked unless a new target-domain
  EvidenceCondition is supplied.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from vaig.rrp.evidence import EvidenceCondition
from vaig.rrp.risk_contract import RiskDomain, get_risk_contract, is_domain_isolated


@dataclass
class Intent:
    intent_id: str
    created_at: str
    operator_id: str
    evidence_id: str
    evidence_condition_snapshot: Dict
    action_type: str
    action_parameters: Dict[str, Any]
    expected_outcome: str

    source_domain: str
    target_domain: str
    cross_domain: bool

    authorization_status: str
    authorization_authority: Optional[str]
    authorization_timestamp: Optional[str]
    authorization_reasoning: Optional[str]

    def __post_init__(self):
        if self.evidence_condition_snapshot.get("validation_status") not in (
            "validated",
            "overridden",
        ):
            raise ValueError(
                f"INTENT_BLOCKED: EvidenceCondition {self.evidence_id} has status "
                f"'{self.evidence_condition_snapshot.get('validation_status')}'. "
                "Required: 'validated' or 'overridden'."
            )

        if self.cross_domain and is_domain_isolated(
            RiskDomain(self.source_domain), RiskDomain(self.target_domain)
        ):
            raise ValueError(
                f"INTENT_BLOCKED: Cross-domain intent from {self.source_domain} to "
                f"{self.target_domain} is ISOLATED by risk contract. "
                "New EvidenceCondition required for target domain."
            )

    def to_dict(self):
        return asdict(self)


class IntentFactory:
    """Factory with RiskContract and domain-segmentation checks."""

    _active_domains: Dict[str, str] = {}

    @classmethod
    def create(
        cls,
        intent_id: str,
        operator_id: str,
        evidence_condition: EvidenceCondition,
        action_type: str,
        action_parameters: Dict[str, Any],
        expected_outcome: str,
        source_domain: Optional[str] = None,
        target_domain: Optional[str] = None,
    ) -> Intent:
        if not evidence_condition.is_admissible():
            raise ValueError(
                f"INTENT_BLOCKED: EvidenceCondition {evidence_condition.evidence_id} "
                f"is not admissible (status: {evidence_condition.validation_status})."
            )

        contract = get_risk_contract(action_type)

        if source_domain is None:
            source_domain = cls._active_domains.get(operator_id, "general")
        if target_domain is None:
            target_domain = contract["domain"]

        cross_domain = source_domain != target_domain

        if cross_domain and is_domain_isolated(
            RiskDomain(source_domain), RiskDomain(target_domain)
        ):
            raise ValueError(
                f"INTENT_BLOCKED: Cross-domain intent from {source_domain} to "
                f"{target_domain} is ISOLATED. New EvidenceCondition required."
            )

        evidence_condition.bound_intents.append(intent_id)
        cls._active_domains[operator_id] = target_domain

        return Intent(
            intent_id=intent_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            operator_id=operator_id,
            evidence_id=evidence_condition.evidence_id,
            evidence_condition_snapshot=evidence_condition.to_dict(),
            action_type=action_type,
            action_parameters=action_parameters,
            expected_outcome=expected_outcome,
            source_domain=source_domain,
            target_domain=target_domain,
            cross_domain=cross_domain,
            authorization_status="PENDING",
            authorization_authority=None,
            authorization_timestamp=None,
            authorization_reasoning=None,
        )

    @classmethod
    def reset_domain(cls, operator_id: str):
        """Reset operator domain context for tests or explicit operational reset."""
        cls._active_domains.pop(operator_id, None)
