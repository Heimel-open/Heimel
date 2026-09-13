"""
ACS Policy Engine v0.1
Evaluates packets against policy rules and returns one of 6 primitives.
"""

from typing import List, Dict, Any
from datetime import datetime, timezone
from enum import Enum

class Decision(Enum):
    ALLOW = "ALLOW"
    MODIFY = "MODIFY"
    DEFER = "DEFER"
    DENY = "DENY"
    STEP_UP = "STEP_UP"
    HALT = "HALT"

class ACSPolicyEngine:
    """
    ACS Policy Engine v0.1

    Priority order (highest first):
    1. HALT   - Critical risk
    2. DENY   - Risk exceeds policy max
    3. STEP_UP - High risk or signoff required
    4. DEFER  - Evidence gap too high
    5. MODIFY - Low confidence, evidence OK
    6. ALLOW  - All checks pass
    """

    RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}

    def __init__(self):
        self.decision_log = []

    def evaluate(self, packet: Dict[str, Any]) -> Decision:
        policy = packet.get("policy", {})
        risk = packet.get("risk", {})
        evidence = packet.get("evidence", {})
        confidence = packet.get("confidence", 0)

        risk_level = risk.get("level", "low")
        max_risk = policy.get("max_risk_level", "critical")
        evidence_gap = evidence.get("evidence_gap", 0)
        gap_threshold = policy.get("evidence_gap_threshold", 0.30)
        required_signoff = policy.get("required_signoff", False)

        # HALT: Critical risk
        if risk_level == "critical":
            self._log(packet, Decision.HALT, "Risk level is CRITICAL")
            return Decision.HALT

        # DENY: Risk exceeds policy max
        if self.RISK_ORDER.get(risk_level, 0) > self.RISK_ORDER.get(max_risk, 3):
            self._log(packet, Decision.DENY, 
                f"Risk {risk_level} exceeds policy max {max_risk}")
            return Decision.DENY

        # STEP_UP: High risk OR required signoff
        if risk_level == "high" or required_signoff:
            self._log(packet, Decision.STEP_UP, 
                f"Risk={risk_level}, signoff={required_signoff}")
            return Decision.STEP_UP

        # DEFER: Evidence gap too high
        if evidence_gap > gap_threshold:
            self._log(packet, Decision.DEFER,
                f"Evidence gap {evidence_gap} > threshold {gap_threshold}")
            return Decision.DEFER

        # MODIFY: Low confidence, evidence OK
        if confidence < 0.90 and evidence_gap <= gap_threshold:
            self._log(packet, Decision.MODIFY,
                f"Confidence {confidence} < 0.90, evidence OK")
            return Decision.MODIFY

        # ALLOW: All checks pass
        self._log(packet, Decision.ALLOW, "All policy checks passed")
        return Decision.ALLOW

    def _log(self, packet: Dict[str, Any], decision: Decision, reason: str):
        self.decision_log.append({
            "packet_id": packet.get("packet_id"),
            "decision": decision.value,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def get_log(self) -> List[Dict]:
        return self.decision_log
