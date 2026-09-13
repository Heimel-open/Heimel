"""Organizational Memory: Stores organizational patterns and cross-user insights."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum


class PatternType(Enum):
    """Types of organizational patterns."""
    APPROVAL_CHAIN = "approval_chain"
    RISK_CONCENTRATION = "risk_concentration"
    POLICY_VIOLATION_TREND = "policy_violation_trend"
    DECISION_PATTERN = "decision_pattern"
    ESCALATION_PATTERN = "escalation_pattern"
    COLLABORATION_PATTERN = "collaboration_pattern"
    SKILL_PATTERN = "skill_pattern"
    GOVERNANCE_DRIFT = "governance_drift"


@dataclass
class OrganizationalPattern:
    """Represents a learned organizational pattern."""
    pattern_id: str
    pattern_type: PatternType
    description: str
    confidence: float  # 0.0-1.0
    affected_users: List[str] = field(default_factory=list)
    affected_actions: List[str] = field(default_factory=list)
    evidence_count: int = 0
    first_detected: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    recommendation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class OrganizationalMemory:
    """
    Stores and retrieves organizational-level memory.

    Tracks:
    - Approval chains and escalation patterns
    - Risk concentrations
    - Policy violation trends
    - Decision patterns across organization
    - Governance drift
    - Collaboration patterns
    - Skill and capability distribution
    """

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.patterns: Dict[str, OrganizationalPattern] = {}
        self.roles: Dict[str, Dict[str, Any]] = {}
        self.policies: Dict[str, Dict[str, Any]] = {}
        self.regulations: Dict[str, Dict[str, Any]] = {}

    def detect_pattern(
        self,
        pattern_id: str,
        pattern_type: PatternType,
        description: str,
        affected_users: List[str],
        affected_actions: List[str],
        confidence: float,
        recommendation: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> OrganizationalPattern:
        """Detect and record an organizational pattern."""
        pattern = OrganizationalPattern(
            pattern_id=pattern_id,
            pattern_type=pattern_type,
            description=description,
            affected_users=affected_users,
            affected_actions=affected_actions,
            confidence=confidence,
            recommendation=recommendation,
            metadata=metadata or {},
        )
        self.patterns[pattern_id] = pattern
        return pattern

    def get_patterns_by_type(self, pattern_type: PatternType) -> List[OrganizationalPattern]:
        """Get patterns of a specific type."""
        return [p for p in self.patterns.values() if p.pattern_type == pattern_type]

    def get_high_confidence_patterns(self, threshold: float = 0.7) -> List[OrganizationalPattern]:
        """Get patterns with high confidence."""
        return [
            p for p in self.patterns.values()
            if p.confidence >= threshold
        ]

    def get_patterns_affecting_user(self, user_id: str) -> List[OrganizationalPattern]:
        """Get patterns that affect a specific user."""
        return [
            p for p in self.patterns.values()
            if user_id in p.affected_users
        ]

    def get_patterns_affecting_action(self, action_type: str) -> List[OrganizationalPattern]:
        """Get patterns that affect a specific action type."""
        return [
            p for p in self.patterns.values()
            if action_type in p.affected_actions
        ]

    def register_role(
        self,
        role_id: str,
        role_name: str,
        responsibilities: List[str],
        authority_limits: Dict[str, Any],
        users_in_role: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Register an organizational role."""
        role = {
            "role_id": role_id,
            "role_name": role_name,
            "responsibilities": responsibilities,
            "authority_limits": authority_limits,
            "users_in_role": users_in_role or [],
            "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
        }
        self.roles[role_id] = role
        return role

    def get_role(self, role_id: str) -> Optional[Dict[str, Any]]:
        """Get role information."""
        return self.roles.get(role_id)

    def register_policy(
        self,
        policy_id: str,
        policy_name: str,
        policy_text: str,
        applies_to_roles: List[str],
        applies_to_actions: List[str],
        effective_date: datetime,
        expiration_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Register an organizational policy."""
        policy = {
            "policy_id": policy_id,
            "policy_name": policy_name,
            "policy_text": policy_text,
            "applies_to_roles": applies_to_roles,
            "applies_to_actions": applies_to_actions,
            "effective_date": effective_date,
            "expiration_date": expiration_date,
            "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
            "is_active": True,
        }
        self.policies[policy_id] = policy
        return policy

    def get_applicable_policies(
        self,
        user_role: str,
        action_type: str
    ) -> List[Dict[str, Any]]:
        """Get policies applicable to a user and action."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return [
            p for p in self.policies.values()
            if p["is_active"]
            and p["effective_date"] <= now
            and (p["expiration_date"] is None or p["expiration_date"] > now)
            and user_role in p["applies_to_roles"]
            and action_type in p["applies_to_actions"]
        ]

    def register_regulation(
        self,
        regulation_id: str,
        regulation_name: str,
        jurisdiction: str,
        description: str,
        relevant_articles: List[str],
        compliance_owner: str
    ) -> Dict[str, Any]:
        """Register a regulatory requirement."""
        regulation = {
            "regulation_id": regulation_id,
            "regulation_name": regulation_name,
            "jurisdiction": jurisdiction,
            "description": description,
            "relevant_articles": relevant_articles,
            "compliance_owner": compliance_owner,
            "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
        }
        self.regulations[regulation_id] = regulation
        return regulation

    def get_applicable_regulations(self, domain: str) -> List[Dict[str, Any]]:
        """Get regulations applicable to a domain."""
        return [
            r for r in self.regulations.values()
            if domain.lower() in r.get("relevant_articles", [])
            or domain.lower() in r["description"].lower()
        ]

    def get_organization_summary(self) -> Dict[str, Any]:
        """Get a summary of organizational state."""
        return {
            "tenant_id": self.tenant_id,
            "total_patterns": len(self.patterns),
            "high_confidence_patterns": len(self.get_high_confidence_patterns()),
            "total_roles": len(self.roles),
            "total_policies": len(self.policies),
            "active_policies": sum(1 for p in self.policies.values() if p["is_active"]),
            "total_regulations": len(self.regulations),
            "pattern_types_detected": list(set(p.pattern_type.value for p in self.patterns.values())),
        }

    def get_governance_drift_report(self) -> Dict[str, Any]:
        """Get report on governance drift."""
        drift_patterns = self.get_patterns_by_type(PatternType.GOVERNANCE_DRIFT)
        return {
            "drift_patterns_detected": len(drift_patterns),
            "high_confidence_drift": [
                {
                    "pattern_id": p.pattern_id,
                    "description": p.description,
                    "confidence": p.confidence,
                    "affected_users": p.affected_users,
                    "recommendation": p.recommendation,
                }
                for p in drift_patterns
                if p.confidence >= 0.7
            ],
            "drift_severity": "low" if len(drift_patterns) == 0 else (
                "medium" if len(drift_patterns) <= 3 else "high"
            ),
        }
