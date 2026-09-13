"""User Memory: Stores user preferences, decisions, and outcomes."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum


class DecisionOutcomeType(Enum):
    """Types of decision outcomes."""
    APPROVED = "approved"
    DENIED = "denied"
    ESCALATED = "escalated"
    DEFERRED = "deferred"
    MODIFIED = "modified"
    HALTED = "halted"


@dataclass
class UserPreferences:
    """User preferences for advisor behavior."""
    user_id: str
    preferred_advisor_role: str = "advisor"
    preferred_activation_mode: str = "manual"
    auto_escalate_threshold: float = 0.7
    confidence_threshold: float = 0.5
    verbose_mode: bool = False
    notifications_enabled: bool = True
    prefer_email_summaries: bool = False
    timezone: str = "UTC"
    language: str = "en"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Decision:
    """Represents a recorded decision."""
    decision_id: str
    user_id: str
    action_type: str  # email, approve_expense, share_document, etc.
    intent: str
    resource_id: Optional[str]
    governance_decision: str  # ALLOW, DENY, STEP_UP, etc.
    confidence: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    authority_checked: bool = False
    evidence_used: List[str] = field(default_factory=list)
    policy_refs: List[str] = field(default_factory=list)
    outcome: Optional["DecisionOutcome"] = None


@dataclass
class DecisionOutcome:
    """Outcome of a decision after execution."""
    decision_id: str
    outcome_type: DecisionOutcomeType
    success: bool
    result_summary: str
    feedback: Optional[str] = None
    actual_impact: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class UserMemory:
    """
    Stores and retrieves user-specific memory.

    Tracks:
    - User preferences and settings
    - Prior decisions and approvals
    - Approved constraints and limits
    - Risk tracking for this user
    - Unresolved issues
    - Active projects and context
    - Outcome tracking and feedback
    """

    def __init__(self, user_id: str, tenant_id: str):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.preferences = UserPreferences(user_id=user_id)
        self.decisions: Dict[str, Decision] = {}
        self.approvals: Dict[str, Dict[str, Any]] = {}
        self.constraints: Dict[str, Dict[str, Any]] = {}
        self.risks: Dict[str, Dict[str, Any]] = {}
        self.active_projects: Dict[str, Dict[str, Any]] = {}

    def update_preferences(
        self,
        preferred_advisor_role: Optional[str] = None,
        preferred_activation_mode: Optional[str] = None,
        auto_escalate_threshold: Optional[float] = None,
        confidence_threshold: Optional[float] = None,
        **kwargs
    ) -> UserPreferences:
        """Update user preferences."""
        if preferred_advisor_role:
            self.preferences.preferred_advisor_role = preferred_advisor_role
        if preferred_activation_mode:
            self.preferences.preferred_activation_mode = preferred_activation_mode
        if auto_escalate_threshold is not None:
            self.preferences.auto_escalate_threshold = auto_escalate_threshold
        if confidence_threshold is not None:
            self.preferences.confidence_threshold = confidence_threshold

        for key, value in kwargs.items():
            if hasattr(self.preferences, key):
                setattr(self.preferences, key, value)

        self.preferences.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        return self.preferences

    def record_decision(
        self,
        decision_id: str,
        action_type: str,
        intent: str,
        governance_decision: str,
        confidence: float = 0.8,
        resource_id: Optional[str] = None,
        authority_checked: bool = False,
        evidence_used: Optional[List[str]] = None,
        policy_refs: Optional[List[str]] = None
    ) -> Decision:
        """Record a decision."""
        decision = Decision(
            decision_id=decision_id,
            user_id=self.user_id,
            action_type=action_type,
            intent=intent,
            resource_id=resource_id,
            governance_decision=governance_decision,
            confidence=confidence,
            authority_checked=authority_checked,
            evidence_used=evidence_used or [],
            policy_refs=policy_refs or [],
        )
        self.decisions[decision_id] = decision
        return decision

    def record_decision_outcome(
        self,
        decision_id: str,
        outcome_type: DecisionOutcomeType,
        success: bool,
        result_summary: str,
        feedback: Optional[str] = None,
        actual_impact: Optional[Dict[str, Any]] = None
    ) -> Optional[DecisionOutcome]:
        """Record outcome of a decision."""
        if decision_id not in self.decisions:
            return None

        outcome = DecisionOutcome(
            decision_id=decision_id,
            outcome_type=outcome_type,
            success=success,
            result_summary=result_summary,
            feedback=feedback,
            actual_impact=actual_impact,
        )

        self.decisions[decision_id].outcome = outcome
        return outcome

    def get_decision_history(self, action_type: Optional[str] = None) -> List[Decision]:
        """Get decision history, optionally filtered by action type."""
        decisions = list(self.decisions.values())
        if action_type:
            decisions = [d for d in decisions if d.action_type == action_type]
        return sorted(decisions, key=lambda d: d.timestamp, reverse=True)

    def record_approval(
        self,
        approval_id: str,
        action_type: str,
        target: str,
        amount: Optional[float] = None,
        valid_until: Optional[datetime] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record an approval or delegation."""
        approval = {
            "approval_id": approval_id,
            "action_type": action_type,
            "target": target,
            "amount": amount,
            "valid_until": valid_until,
            "notes": notes,
            "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
        }
        self.approvals[approval_id] = approval
        return approval

    def get_valid_approvals(self) -> List[Dict[str, Any]]:
        """Get all currently valid approvals."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return [
            a for a in self.approvals.values()
            if a["valid_until"] is None or a["valid_until"] > now
        ]

    def record_constraint(
        self,
        constraint_id: str,
        constraint_type: str,
        limit_value: Any,
        applies_to: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record a constraint or limit."""
        constraint = {
            "constraint_id": constraint_id,
            "constraint_type": constraint_type,
            "limit_value": limit_value,
            "applies_to": applies_to,
            "reason": reason,
            "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
        }
        self.constraints[constraint_id] = constraint
        return constraint

    def get_applicable_constraints(self, action_type: str) -> List[Dict[str, Any]]:
        """Get constraints applicable to an action type."""
        return [
            c for c in self.constraints.values()
            if c["applies_to"] == action_type or c["applies_to"] == "*"
        ]

    def track_risk(
        self,
        risk_id: str,
        risk_type: str,
        severity: str,
        description: str,
        related_actions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Track a risk associated with this user."""
        risk = {
            "risk_id": risk_id,
            "risk_type": risk_type,
            "severity": severity,
            "description": description,
            "related_actions": related_actions or [],
            "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
            "resolved": False,
        }
        self.risks[risk_id] = risk
        return risk

    def get_unresolved_risks(self) -> List[Dict[str, Any]]:
        """Get unresolved risks."""
        return [r for r in self.risks.values() if not r["resolved"]]

    def resolve_risk(self, risk_id: str, resolution: str) -> Optional[Dict[str, Any]]:
        """Resolve a risk."""
        if risk_id not in self.risks:
            return None

        self.risks[risk_id]["resolved"] = True
        self.risks[risk_id]["resolution"] = resolution
        self.risks[risk_id]["resolved_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
        return self.risks[risk_id]

    def add_active_project(
        self,
        project_id: str,
        project_name: str,
        description: str,
        context_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Track an active project."""
        project = {
            "project_id": project_id,
            "project_name": project_name,
            "description": description,
            "context_data": context_data or {},
            "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
            "is_active": True,
        }
        self.active_projects[project_id] = project
        return project

    def get_active_projects(self) -> List[Dict[str, Any]]:
        """Get currently active projects."""
        return [p for p in self.active_projects.values() if p["is_active"]]

    def close_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Close an active project."""
        if project_id not in self.active_projects:
            return None

        self.active_projects[project_id]["is_active"] = False
        self.active_projects[project_id]["closed_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
        return self.active_projects[project_id]

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of user memory."""
        return {
            "user_id": self.user_id,
            "preferences": self.preferences.__dict__,
            "total_decisions": len(self.decisions),
            "successful_decisions": sum(
                1 for d in self.decisions.values()
                if d.outcome and d.outcome.success
            ),
            "active_approvals": len(self.get_valid_approvals()),
            "active_constraints": len(self.constraints),
            "unresolved_risks": len(self.get_unresolved_risks()),
            "active_projects": len(self.get_active_projects()),
        }
