"""Tests for Enterprise Memory system."""

import pytest
from datetime import datetime, timedelta, timezone
from src.valo_platform.enterprise_memory import (
    UserMemory,
    UserPreferences,
    Decision,
    OrganizationalMemory,
    MemoryEngine,
)
from src.valo_platform.enterprise_memory.user_memory import DecisionOutcomeType
from src.valo_platform.enterprise_memory.organizational_memory import PatternType


class TestUserMemory:
    """Test user-specific memory."""

    def test_create_user_memory(self):
        """Test creating user memory."""
        memory = UserMemory("user_123", "tenant_001")
        assert memory.user_id == "user_123"
        assert memory.tenant_id == "tenant_001"

    def test_update_preferences(self):
        """Test updating user preferences."""
        memory = UserMemory("user_123", "tenant_001")
        prefs = memory.update_preferences(
            preferred_advisor_role="advisor",
            auto_escalate_threshold=0.8,
        )

        assert prefs.preferred_advisor_role == "advisor"
        assert prefs.auto_escalate_threshold == 0.8

    def test_record_decision(self):
        """Test recording a decision."""
        memory = UserMemory("user_123", "tenant_001")
        decision = memory.record_decision(
            decision_id="dec_001",
            action_type="email_send",
            intent="Send customer email",
            governance_decision="ALLOW",
            confidence=0.9,
        )

        assert decision.decision_id == "dec_001"
        assert decision.action_type == "email_send"
        assert len(memory.decisions) == 1

    def test_record_decision_outcome(self):
        """Test recording decision outcome."""
        memory = UserMemory("user_123", "tenant_001")
        memory.record_decision(
            decision_id="dec_001",
            action_type="email_send",
            intent="Send email",
            governance_decision="ALLOW",
        )

        outcome = memory.record_decision_outcome(
            decision_id="dec_001",
            outcome_type=DecisionOutcomeType.APPROVED,
            success=True,
            result_summary="Email sent successfully",
        )

        assert outcome is not None
        assert outcome.success is True
        assert memory.decisions["dec_001"].outcome == outcome

    def test_decision_history(self):
        """Test getting decision history."""
        memory = UserMemory("user_123", "tenant_001")
        for i in range(3):
            memory.record_decision(
                decision_id=f"dec_{i}",
                action_type="email_send",
                intent="Send email",
                governance_decision="ALLOW",
            )

        history = memory.get_decision_history()
        assert len(history) == 3

    def test_approval_management(self):
        """Test approval tracking."""
        memory = UserMemory("user_123", "tenant_001")
        approval = memory.record_approval(
            approval_id="appr_001",
            action_type="approve_expense",
            target="expense_123",
            amount=10000,
            valid_until=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30),
        )

        assert approval["approval_id"] == "appr_001"
        assert len(memory.get_valid_approvals()) == 1

    def test_constraint_management(self):
        """Test constraint tracking."""
        memory = UserMemory("user_123", "tenant_001")
        constraint = memory.record_constraint(
            constraint_id="con_001",
            constraint_type="daily_limit",
            limit_value=50000,
            applies_to="expense_approval",
            reason="Budget constraint",
        )

        assert constraint["constraint_id"] == "con_001"
        constraints = memory.get_applicable_constraints("expense_approval")
        assert len(constraints) == 1

    def test_risk_tracking(self):
        """Test risk tracking."""
        memory = UserMemory("user_123", "tenant_001")
        risk = memory.track_risk(
            risk_id="risk_001",
            risk_type="compliance",
            severity="high",
            description="Policy violation detected",
        )

        assert risk["risk_id"] == "risk_001"
        unresolved = memory.get_unresolved_risks()
        assert len(unresolved) == 1

    def test_resolve_risk(self):
        """Test resolving a risk."""
        memory = UserMemory("user_123", "tenant_001")
        memory.track_risk(
            risk_id="risk_001",
            risk_type="compliance",
            severity="high",
            description="Policy violation",
        )

        resolved = memory.resolve_risk("risk_001", "Policy updated and acknowledged")
        assert resolved["resolved"] is True

    def test_project_management(self):
        """Test active project tracking."""
        memory = UserMemory("user_123", "tenant_001")
        project = memory.add_active_project(
            project_id="proj_001",
            project_name="Q3 Initiative",
            description="Compliance upgrade project",
        )

        assert project["project_id"] == "proj_001"
        active = memory.get_active_projects()
        assert len(active) == 1

    def test_memory_summary(self):
        """Test getting memory summary."""
        memory = UserMemory("user_123", "tenant_001")
        memory.record_decision(
            decision_id="dec_001",
            action_type="email_send",
            intent="Send email",
            governance_decision="ALLOW",
        )
        memory.record_approval(
            approval_id="appr_001",
            action_type="approve_expense",
            target="exp_123",
        )

        summary = memory.get_summary()
        assert summary["user_id"] == "user_123"
        assert summary["total_decisions"] == 1
        assert summary["active_approvals"] == 1


class TestOrganizationalMemory:
    """Test organizational memory."""

    def test_create_organizational_memory(self):
        """Test creating organizational memory."""
        memory = OrganizationalMemory("tenant_001")
        assert memory.tenant_id == "tenant_001"

    def test_detect_pattern(self):
        """Test detecting patterns."""
        memory = OrganizationalMemory("tenant_001")
        pattern = memory.detect_pattern(
            pattern_id="pat_001",
            pattern_type=PatternType.APPROVAL_CHAIN,
            description="High-risk approvals require CFO sign-off",
            affected_users=["user_1", "user_2"],
            affected_actions=["approve_large_expense"],
            confidence=0.85,
        )

        assert pattern.pattern_id == "pat_001"
        assert len(memory.patterns) == 1

    def test_pattern_retrieval(self):
        """Test retrieving patterns by type."""
        memory = OrganizationalMemory("tenant_001")
        for i in range(3):
            memory.detect_pattern(
                pattern_id=f"pat_{i}",
                pattern_type=PatternType.APPROVAL_CHAIN,
                description=f"Pattern {i}",
                affected_users=[],
                affected_actions=[],
                confidence=0.7,
            )

        patterns = memory.get_patterns_by_type(PatternType.APPROVAL_CHAIN)
        assert len(patterns) == 3

    def test_high_confidence_patterns(self):
        """Test filtering high confidence patterns."""
        memory = OrganizationalMemory("tenant_001")
        memory.detect_pattern(
            pattern_id="pat_001",
            pattern_type=PatternType.RISK_CONCENTRATION,
            description="Low confidence",
            affected_users=[],
            affected_actions=[],
            confidence=0.5,
        )
        memory.detect_pattern(
            pattern_id="pat_002",
            pattern_type=PatternType.RISK_CONCENTRATION,
            description="High confidence",
            affected_users=[],
            affected_actions=[],
            confidence=0.85,
        )

        high_conf = memory.get_high_confidence_patterns(0.7)
        assert len(high_conf) == 1
        assert high_conf[0].pattern_id == "pat_002"

    def test_role_management(self):
        """Test role registration and retrieval."""
        memory = OrganizationalMemory("tenant_001")
        role = memory.register_role(
            role_id="role_manager",
            role_name="Manager",
            responsibilities=["Approve expenses"],
            authority_limits={"daily": 50000},
        )

        assert role["role_id"] == "role_manager"
        retrieved = memory.get_role("role_manager")
        assert retrieved is not None

    def test_policy_management(self):
        """Test policy registration and retrieval."""
        memory = OrganizationalMemory("tenant_001")
        policy = memory.register_policy(
            policy_id="pol_001",
            policy_name="Expense Policy",
            policy_text="All expenses over 10k require approval",
            applies_to_roles=["manager"],
            applies_to_actions=["expense_approval"],
            effective_date=datetime.now(timezone.utc).replace(tzinfo=None),
        )

        assert policy["policy_id"] == "pol_001"
        applicable = memory.get_applicable_policies("manager", "expense_approval")
        assert len(applicable) == 1

    def test_regulation_management(self):
        """Test regulation tracking."""
        memory = OrganizationalMemory("tenant_001")
        regulation = memory.register_regulation(
            regulation_id="reg_001",
            regulation_name="GDPR",
            jurisdiction="EU",
            description="Data privacy regulation",
            relevant_articles=["article_5", "article_32"],
            compliance_owner="DPO",
        )

        assert regulation["regulation_id"] == "reg_001"
        applicable = memory.get_applicable_regulations("article_5")
        assert len(applicable) == 1

    def test_governance_drift_report(self):
        """Test governance drift reporting."""
        memory = OrganizationalMemory("tenant_001")
        memory.detect_pattern(
            pattern_id="pat_drift",
            pattern_type=PatternType.GOVERNANCE_DRIFT,
            description="Escalation threshold drift detected",
            affected_users=["user_1"],
            affected_actions=["approvals"],
            confidence=0.8,
            recommendation="Review and realign policies",
        )

        report = memory.get_governance_drift_report()
        assert report["drift_patterns_detected"] == 1
        assert report["drift_severity"] in ["low", "medium"]


class TestMemoryEngine:
    """Test memory engine orchestration."""

    def test_create_memory_engine(self):
        """Test creating memory engine."""
        engine = MemoryEngine("tenant_001")
        assert engine.tenant_id == "tenant_001"

    def test_user_memory_creation(self):
        """Test getting or creating user memory."""
        engine = MemoryEngine("tenant_001")
        memory = engine.get_or_create_user_memory("user_123")

        assert memory.user_id == "user_123"
        assert len(engine.user_memories) == 1

    def test_record_decision_with_context(self):
        """Test recording decision in engine."""
        engine = MemoryEngine("tenant_001")
        dec_id = engine.record_decision_with_context(
            user_id="user_123",
            decision_id="dec_001",
            action_type="email_send",
            intent="Send email",
            governance_decision="ALLOW",
            confidence=0.85,
        )

        assert dec_id == "dec_001"
        user_memory = engine.get_or_create_user_memory("user_123")
        assert "dec_001" in user_memory.decisions

    def test_detect_approval_chain(self):
        """Test approval chain detection."""
        engine = MemoryEngine("tenant_001")

        # Default chain for low amount
        chain = engine.detect_approval_chain("expense_approval", amount=5000)
        assert "manager" in chain

        # Escalated chain for high amount
        chain = engine.detect_approval_chain("expense_approval", amount=100000)
        assert "cfo" in chain

    def test_user_context_snapshot(self):
        """Test getting user context snapshot."""
        engine = MemoryEngine("tenant_001")
        engine.record_decision_with_context(
            user_id="user_123",
            decision_id="dec_001",
            action_type="email_send",
            intent="Send email",
            governance_decision="ALLOW",
        )

        snapshot = engine.get_user_context_snapshot("user_123")
        assert snapshot["user_id"] == "user_123"
        assert snapshot["decision_stats"]["total_decisions"] == 1

    def test_organizational_context_snapshot(self):
        """Test getting organizational context snapshot."""
        engine = MemoryEngine("tenant_001")
        engine.organizational_memory.detect_pattern(
            pattern_id="pat_001",
            pattern_type=PatternType.APPROVAL_CHAIN,
            description="Test pattern",
            affected_users=[],
            affected_actions=[],
            confidence=0.8,
        )

        snapshot = engine.get_organizational_context_snapshot()
        assert snapshot["tenant_id"] == "tenant_001"
        assert len(snapshot["high_confidence_insights"]) > 0

    def test_suggest_next_action(self):
        """Test suggesting next action."""
        engine = MemoryEngine("tenant_001")

        suggestion = engine.suggest_next_action(
            user_id="user_123",
            action_type="expense_approval",
            amount=25000,
        )

        assert suggestion["action_type"] == "expense_approval"
        assert "recommended_approval_chain" in suggestion
        assert "recommendation" in suggestion

    def test_memory_stats(self):
        """Test getting memory statistics."""
        engine = MemoryEngine("tenant_001")
        engine.record_decision_with_context(
            user_id="user_123",
            decision_id="dec_001",
            action_type="email_send",
            intent="Send email",
            governance_decision="ALLOW",
        )
        engine.record_decision_with_context(
            user_id="user_456",
            decision_id="dec_002",
            action_type="approve_expense",
            intent="Approve",
            governance_decision="DENY",
        )

        stats = engine.get_memory_stats()
        assert stats["total_users_tracked"] == 2
        assert stats["total_decisions_recorded"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
