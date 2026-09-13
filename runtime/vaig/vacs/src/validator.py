"""
ACS Validator v0.1
Validates ACS Packet structure against schema-level invariants.
"""

from enum import Enum
from typing import Any, Dict, List


class Decision(Enum):
    ALLOW = "ALLOW"
    MODIFY = "MODIFY"
    DEFER = "DEFER"
    DENY = "DENY"
    STEP_UP = "STEP_UP"
    HALT = "HALT"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceType(Enum):
    DOCUMENT = "document"
    POLICY = "policy"
    DATA = "data"
    TEST_RESULT = "test_result"
    HUMAN_INPUT = "human_input"
    RECIPIENT = "recipient"
    CONTENT = "content"
    ACCOUNT = "account"
    AUTHORIZATION = "authorization"
    CODE_REVIEW = "code_review"
    BACKUP_CONFIRMATION = "backup_confirmation"


class ACSValidationError(Exception):
    pass


class ACSValidator:
    """
    ACS Packet Validator v0.1.
    Validates structure, types, required fields and primitive enums.
    """

    RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}

    def __init__(self):
        self.errors = []

    def validate(self, packet: Dict[str, Any]) -> bool:
        self.errors = []

        required = [
            "acs_version",
            "packet_id",
            "agent_id",
            "timestamp",
            "intent",
            "evidence",
            "risk",
            "confidence",
            "policy",
            "decision",
        ]

        for field in required:
            if field not in packet:
                self.errors.append(f"Missing required field: {field}")

        if self.errors:
            return False

        if packet.get("acs_version") != "0.1":
            self.errors.append(f"Unsupported ACS version: {packet.get('acs_version')}")

        valid_decisions = [d.value for d in Decision]
        if packet.get("decision") not in valid_decisions:
            self.errors.append(
                f"Invalid decision: {packet.get('decision')}. Must be one of {valid_decisions}"
            )

        valid_risks = [r.value for r in RiskLevel]
        risk_level = packet.get("risk", {}).get("level")
        if risk_level not in valid_risks:
            self.errors.append(f"Invalid risk level: {risk_level}")

        confidence = packet.get("confidence")
        if confidence is not None and not (0 <= confidence <= 1):
            self.errors.append(f"Confidence must be 0-1, got {confidence}")

        evidence_gap = packet.get("evidence", {}).get("evidence_gap")
        if evidence_gap is not None and not (0 <= evidence_gap <= 1):
            self.errors.append(f"Evidence gap must be 0-1, got {evidence_gap}")

        valid_evidence_types = [e.value for e in EvidenceType]
        sources = packet.get("evidence", {}).get("sources", [])
        for i, source in enumerate(sources):
            if "hash" not in source:
                self.errors.append(f"Evidence source [{i}] missing 'hash'")
            source_type = source.get("type")
            if source_type is None:
                self.errors.append(f"Evidence source [{i}] missing 'type'")
            elif source_type not in valid_evidence_types:
                self.errors.append(
                    f"Invalid evidence source [{i}] type: {source_type}. Must be one of {valid_evidence_types}"
                )

        policy = packet.get("policy", {})
        policy_required = ["required_signoff", "max_risk_level", "evidence_gap_threshold"]
        for field in policy_required:
            if field not in policy:
                self.errors.append(f"Policy missing required field: {field}")

        max_risk = policy.get("max_risk_level")
        if max_risk is not None and max_risk not in valid_risks:
            self.errors.append(f"Invalid policy max risk level: {max_risk}")

        threshold = policy.get("evidence_gap_threshold")
        if threshold is not None and not (0 <= threshold <= 1):
            self.errors.append(f"Evidence gap threshold must be 0-1, got {threshold}")

        return len(self.errors) == 0

    def get_errors(self) -> List[str]:
        return self.errors
