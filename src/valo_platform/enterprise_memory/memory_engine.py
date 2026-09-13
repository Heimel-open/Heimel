"""Memory Engine: Orchestrates user and organizational memory."""

from typing import Dict, Optional, List, Any
from src.valo_platform.enterprise_memory.user_memory import UserMemory, DecisionOutcomeType
from src.valo_platform.enterprise_memory.organizational_memory import (
    OrganizationalMemory,
    PatternType,
)


class MemoryEngine:
    """
    Orchestrates memory across the enterprise.

    Manages:
    - User-specific memory (preferences, decisions, outcomes)
    - Organizational memory (patterns, policies, regulations)
    - Cross-user insights and learning
    - Memory persistence and retrieval
    """

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.user_memories: Dict[str, UserMemory] = {}
        self.organizational_memory = OrganizationalMemory(tenant_id)

    def get_or_create_user_memory(self, user_id: str) -> UserMemory:
        """Get or create memory for a user."""
        if user_id not in self.user_memories:
            self.user_memories[user_id] = UserMemory(user_id, self.tenant_id)
        return self.user_memories[user_id]

    def record_decision_with_context(
        self,
        user_id: str,
        decision_id: str,
        action_type: str,
        intent: str,
        governance_decision: str,
        confidence: float = 0.8,
        **kwargs
    ) -> str:
        """Record a decision in user memory."""
        user_memory = self.get_or_create_user_memory(user_id)
        decision = user_memory.record_decision(
            decision_id=decision_id,
            action_type=action_type,
            intent=intent,
            governance_decision=governance_decision,
            confidence=confidence,
            **kwargs
        )
        return decision.decision_id

    def record_decision_outcome_with_learning(
        self,
        user_id: str,
        decision_id: str,
        outcome_type: DecisionOutcomeType,
        success: bool,
        result_summary: str,
        feedback: Optional[str] = None,
        actual_impact: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record decision outcome and trigger learning."""
        user_memory = self.get_or_create_user_memory(user_id)
        outcome = user_memory.record_decision_outcome(
            decision_id=decision_id,
            outcome_type=outcome_type,
            success=success,
            result_summary=result_summary,
            feedback=feedback,
            actual_impact=actual_impact,
        )

        if outcome:
            self._analyze_decision_pattern(user_id, decision_id, outcome)

    def _analyze_decision_pattern(
        self,
        user_id: str,
        decision_id: str,
        outcome
    ) -> None:
        """Analyze decision patterns after outcome."""
        user_memory = self.get_or_create_user_memory(user_id)
        decision = user_memory.decisions.get(decision_id)

        if not decision:
            return

        # Check for escalation patterns
        if decision.governance_decision == "STEP_UP":
            escalation_patterns = self.organizational_memory.get_patterns_by_type(
                PatternType.ESCALATION_PATTERN
            )
            if not escalation_patterns or len(escalation_patterns) < 5:
                # Detect pattern after seeing 5+ escalations for same action
                pass

        # Check for policy violations
        if outcome.outcome_type == DecisionOutcomeType.DENIED:
            policy_patterns = self.organizational_memory.get_patterns_by_type(
                PatternType.POLICY_VIOLATION_TREND
            )
            if user_id not in [p.affected_users[0] for p in policy_patterns if p.affected_users]:
                # New policy violation pattern
                pass

    def detect_approval_chain(
        self,
        action_type: str,
        amount: Optional[float] = None
    ) -> List[str]:
        """Detect approval chain for an action."""
        # Analyze historical approvals to detect patterns
        approval_chains = self.organizational_memory.get_patterns_by_type(
            PatternType.APPROVAL_CHAIN
        )

        applicable_chains = [
            p for p in approval_chains
            if action_type in p.affected_actions
        ]

        if applicable_chains:
            # Return the most common chain
            return applicable_chains[0].metadata.get("chain", [])

        # Default chain
        if amount and amount > 50000:
            return ["manager", "finance_director", "cfo"]
        elif amount and amount > 10000:
            return ["manager", "finance"]
        else:
            return ["manager"]

    def get_user_context_snapshot(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive context about a user for advisor."""
        user_memory = self.get_or_create_user_memory(user_id)

        recent_decisions = user_memory.get_decision_history()[:5]
        unresolved_risks = user_memory.get_unresolved_risks()
        active_projects = user_memory.get_active_projects()
        valid_approvals = user_memory.get_valid_approvals()

        return {
            "user_id": user_id,
            "preferences": {
                "advisor_role": user_memory.preferences.preferred_advisor_role,
                "activation_mode": user_memory.preferences.preferred_activation_mode,
            },
            "decision_stats": {
                "total_decisions": len(user_memory.decisions),
                "success_rate": sum(
                    1 for d in user_memory.decisions.values()
                    if d.outcome and d.outcome.success
                ) / max(len(user_memory.decisions), 1),
            },
            "recent_decisions": [
                {
                    "action_type": d.action_type,
                    "governance_decision": d.governance_decision,
                    "timestamp": d.timestamp.isoformat(),
                }
                for d in recent_decisions
            ],
            "unresolved_risks": [
                {
                    "risk_type": r["risk_type"],
                    "severity": r["severity"],
                }
                for r in unresolved_risks
            ],
            "active_projects": [
                {
                    "project_name": p["project_name"],
                    "description": p["description"],
                }
                for p in active_projects
            ],
            "delegated_authorities": [
                {
                    "action_type": a["action_type"],
                    "valid_until": a["valid_until"].isoformat() if a["valid_until"] else None,
                }
                for a in valid_approvals
            ],
        }

    def get_organizational_context_snapshot(self) -> Dict[str, Any]:
        """Get comprehensive organizational context."""
        org_summary = self.organizational_memory.get_organization_summary()
        drift_report = self.organizational_memory.get_governance_drift_report()

        high_confidence_patterns = self.organizational_memory.get_high_confidence_patterns()

        return {
            "tenant_id": self.tenant_id,
            "organization_health": org_summary,
            "governance_drift": drift_report,
            "high_confidence_insights": [
                {
                    "pattern_type": p.pattern_type.value,
                    "description": p.description,
                    "confidence": p.confidence,
                    "recommendation": p.recommendation,
                }
                for p in high_confidence_patterns[:5]
            ],
            "active_policies": org_summary["active_policies"],
            "total_regulations": org_summary["total_regulations"],
        }

    def suggest_next_action(
        self,
        user_id: str,
        action_type: str,
        amount: Optional[float] = None
    ) -> Dict[str, Any]:
        """Suggest next action based on learned patterns."""
        user_memory = self.get_or_create_user_memory(user_id)
        org_memory = self.organizational_memory

        # Get approval chain
        approval_chain = self.detect_approval_chain(action_type, amount)

        # Get applicable policies
        user_role = user_memory.preferences.preferred_advisor_role
        applicable_policies = org_memory.get_applicable_policies(user_role, action_type)

        # Get applicable constraints
        constraints = user_memory.get_applicable_constraints(action_type)

        # Get user's historical success rate for this action
        action_history = [
            d for d in user_memory.decisions.values()
            if d.action_type == action_type
        ]
        success_count = sum(1 for d in action_history if d.outcome and d.outcome.success)
        success_rate = success_count / max(len(action_history), 1)

        return {
            "action_type": action_type,
            "recommended_approval_chain": approval_chain,
            "applicable_policies": [
                {
                    "policy_id": p["policy_id"],
                    "policy_name": p["policy_name"],
                }
                for p in applicable_policies
            ],
            "applicable_constraints": [
                {
                    "constraint_type": c["constraint_type"],
                    "limit_value": c["limit_value"],
                }
                for c in constraints
            ],
            "historical_success_rate": success_rate,
            "recommendation": (
                "Proceed with confidence" if success_rate > 0.8 else
                "Proceed with caution" if success_rate > 0.5 else
                "Escalate before proceeding"
            ),
        }

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about stored memory."""
        total_decisions = sum(
            len(um.decisions) for um in self.user_memories.values()
        )
        total_users = len(self.user_memories)

        return {
            "tenant_id": self.tenant_id,
            "total_users_tracked": total_users,
            "total_decisions_recorded": total_decisions,
            "avg_decisions_per_user": (
                total_decisions / total_users if total_users > 0 else 0
            ),
            "organizational_patterns": len(self.organizational_memory.patterns),
            "high_confidence_patterns": len(
                self.organizational_memory.get_high_confidence_patterns()
            ),
        }
