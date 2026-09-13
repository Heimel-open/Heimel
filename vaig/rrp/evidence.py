"""
EvidenceCondition — Pre-Intent Governance Primitive.

RRP Evidence Pipeline v2 adds RiskContract binding. Validation is contract
execution, not model inference. The original pre-intent invariant remains:
intent cannot form unless evidence is admissible.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from vaig.rrp.risk_contract import get_risk_contract


class EvidenceSourceType(Enum):
    DIRECT_OBSERVATION = "direct_observation"
    MODEL_OUTPUT = "model_output"
    HUMAN_REPORT = "human_report"
    SYSTEM_LOG = "system_log"
    EXTERNAL_FEED = "external_feed"
    INFERENCE_CHAIN = "inference_chain"


class ValidationMethod(Enum):
    CORROBORATION = "corroboration"
    DIRECT_VERIFICATION = "direct_verification"
    CROSS_REFERENCE = "cross_reference"
    TEMPORAL_CONSISTENCY = "temporal_consistency"
    EXPERT_REVIEW = "expert_review"
    AUTOMATED_CHECK = "automated_check"
    UNVALIDATED = "unvalidated"
    CONTRACT_ENFORCED = "contract_enforced"


class ValidationStatus(Enum):
    SUBMITTED = "submitted"
    UNDER_VALIDATION = "under_validation"
    VALIDATED = "validated"
    STALE = "stale"
    CONTESTED = "contested"
    INSUFFICIENT = "insufficient"
    OVERRIDDEN = "overridden"
    CONTRACT_BLOCKED = "contract_blocked"


class ConfidenceLevel(Enum):
    CERTAIN = 1.0
    HIGH = 0.85
    MODERATE = 0.60
    LOW = 0.35
    UNCERTAIN = 0.10
    UNKNOWN = 0.0


@dataclass
class EvidenceSource:
    source_id: str
    source_type: str
    provenance: str
    raw_payload_digest: str
    timestamp_acquired: str
    timestamp_submitted: str

    def to_dict(self):
        return asdict(self)


@dataclass
class EvidenceCondition:
    evidence_id: str
    created_at: str
    source_chain: List[EvidenceSource]

    freshness_boundary_seconds: Optional[int]
    timestamp_validated: Optional[str]
    timestamp_expires: Optional[str]

    validation_status: str
    validator: str
    validation_method: str
    validation_reasoning: str

    confidence_level: str
    confidence_reasoning: str

    contested_by: Optional[str]
    contest_reasoning: Optional[str]

    bound_intents: List[str]

    override_authority: Optional[str] = None
    override_reasoning: Optional[str] = None
    override_timestamp: Optional[str] = None

    # RiskContract binding. Defaults preserve compatibility with the original
    # pre-intent EvidenceCondition constructor.
    action_type: str = "UNKNOWN_ACTION"
    risk_contract_snapshot: Dict[str, Any] = field(
        default_factory=lambda: get_risk_contract("UNKNOWN_ACTION")
    )

    validation_history: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        if self.risk_contract_snapshot is None:
            self.risk_contract_snapshot = get_risk_contract(
                self.action_type or "UNKNOWN_ACTION"
            )
        if not self.action_type:
            self.action_type = "UNKNOWN_ACTION"

    def to_dict(self):
        return asdict(self)

    def append_validation_event(self, event_type: str, actor: str, payload: Dict):
        self.validation_history.append(
            {
                "sequence": len(self.validation_history),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": event_type,
                "actor": actor,
                "payload": payload,
            }
        )

    def is_admissible(self) -> bool:
        return self.validation_status in (
            ValidationStatus.VALIDATED.value,
            ValidationStatus.OVERRIDDEN.value,
        )

    def check_freshness(self) -> bool:
        """Check whether evidence is inside its freshness boundary."""
        if self.freshness_boundary_seconds is None:
            return True
        if self.timestamp_validated is None:
            return False
        validated = datetime.fromisoformat(
            self.timestamp_validated.replace("Z", "+00:00")
        )
        expires = validated + timedelta(seconds=self.freshness_boundary_seconds)
        return datetime.now(timezone.utc) < expires


class EvidenceValidationLifecycle:
    """State machine governed by RiskContract, not system inference."""

    VALID_TRANSITIONS = {
        ValidationStatus.SUBMITTED: [
            ValidationStatus.UNDER_VALIDATION,
            ValidationStatus.INSUFFICIENT,
            ValidationStatus.CONTRACT_BLOCKED,
        ],
        ValidationStatus.UNDER_VALIDATION: [
            ValidationStatus.VALIDATED,
            ValidationStatus.STALE,
            ValidationStatus.CONTESTED,
            ValidationStatus.INSUFFICIENT,
            ValidationStatus.CONTRACT_BLOCKED,
        ],
        ValidationStatus.VALIDATED: [
            ValidationStatus.STALE,
            ValidationStatus.CONTESTED,
        ],
        ValidationStatus.STALE: [
            ValidationStatus.UNDER_VALIDATION,
            ValidationStatus.OVERRIDDEN,
        ],
        ValidationStatus.CONTESTED: [
            ValidationStatus.UNDER_VALIDATION,
            ValidationStatus.OVERRIDDEN,
            ValidationStatus.VALIDATED,
        ],
        ValidationStatus.INSUFFICIENT: [
            ValidationStatus.UNDER_VALIDATION,
            ValidationStatus.OVERRIDDEN,
        ],
        ValidationStatus.CONTRACT_BLOCKED: [ValidationStatus.UNDER_VALIDATION],
        ValidationStatus.OVERRIDDEN: [ValidationStatus.UNDER_VALIDATION],
    }

    def __init__(self, condition: EvidenceCondition):
        self.condition = condition
        self.status = ValidationStatus(condition.validation_status)
        self.contract = condition.risk_contract_snapshot or get_risk_contract(
            condition.action_type or "UNKNOWN_ACTION"
        )

    def transition(
        self, new_status: ValidationStatus, actor: str, payload: Dict[str, Any]
    ):
        if new_status not in self.VALID_TRANSITIONS.get(self.status, []):
            raise ValueError(f"Invalid transition: {self.status.value} → {new_status.value}")

        old_status = self.status
        self.status = new_status
        self.condition.validation_status = new_status.value
        if new_status in (ValidationStatus.VALIDATED, ValidationStatus.OVERRIDDEN):
            self.condition.timestamp_validated = datetime.now(timezone.utc).isoformat()

        self.condition.append_validation_event(
            event_type="VALIDATION_TRANSITION",
            actor=actor,
            payload={
                "from_status": old_status.value,
                "to_status": new_status.value,
                "details": payload,
            },
        )
        return self.status

    def validate_against_contract(self, actor: str = "EVC-VALIDATOR-AUTO"):
        """
        Execute validation based on the active RiskContract.

        This is not model inference. It is deterministic contract execution.
        """
        if self.status == ValidationStatus.SUBMITTED:
            self.transition(
                ValidationStatus.UNDER_VALIDATION,
                actor,
                {"trigger": "Contract validation initiated"},
            )

        contract = self.contract

        if not contract.get("requires_evidence", False):
            self.transition(
                ValidationStatus.VALIDATED,
                actor,
                {
                    "validation_method": ValidationMethod.CONTRACT_ENFORCED.value,
                    "reasoning": (
                        f"Risk tier {contract['tier']} does not require evidence "
                        "per contract."
                    ),
                    "confidence": ConfidenceLevel.HIGH.value,
                },
            )
            self.condition.validation_method = ValidationMethod.CONTRACT_ENFORCED.value
            self.condition.validation_reasoning = (
                f"Risk tier {contract['tier']} does not require evidence per contract."
            )
            self.condition.confidence_level = ConfidenceLevel.HIGH.value
            self.condition.confidence_reasoning = (
                "Contract-enforced: no evidence required."
            )
            return

        if contract.get("requires_corroboration", False):
            source_types = [s.source_type for s in self.condition.source_chain]
            unique_types = set(source_types)

            if len(self.condition.source_chain) < 2 or len(unique_types) < 2:
                reasoning = (
                    "Contract requires corroboration (2+ independent sources). "
                    f"Got {len(self.condition.source_chain)} sources, "
                    f"{len(unique_types)} unique types."
                )
                self.transition(
                    ValidationStatus.INSUFFICIENT,
                    actor,
                    {
                        "validation_method": ValidationMethod.CONTRACT_ENFORCED.value,
                        "reasoning": reasoning,
                        "confidence": ConfidenceLevel.UNCERTAIN.value,
                    },
                )
                self.condition.validation_method = ValidationMethod.CONTRACT_ENFORCED.value
                self.condition.validation_reasoning = reasoning
                self.condition.confidence_level = ConfidenceLevel.UNCERTAIN.value
                self.condition.confidence_reasoning = (
                    "Contract-enforced: corroboration required but not provided."
                )
                return

        self.transition(
            ValidationStatus.VALIDATED,
            actor,
            {
                "validation_method": ValidationMethod.CONTRACT_ENFORCED.value,
                "reasoning": f"All contract requirements met for tier {contract['tier']}.",
                "confidence": ConfidenceLevel.HIGH.value,
            },
        )
        self.condition.validation_method = ValidationMethod.CONTRACT_ENFORCED.value
        self.condition.validation_reasoning = (
            f"All contract requirements met for tier {contract['tier']}."
        )
        self.condition.confidence_level = ConfidenceLevel.HIGH.value
        self.condition.confidence_reasoning = (
            "Contract-enforced: all requirements met."
        )

    def is_admissible_for_intent(self) -> bool:
        return self.condition.is_admissible()
