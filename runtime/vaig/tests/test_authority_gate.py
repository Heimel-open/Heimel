"""Tests for Authority Gate."""

import pytest
from datetime import datetime, timedelta, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
from src.authority_gate import (
    AuthorityGate,
    AuthorityDelegation,
    ExecutionRequest,
    AuthorityDecision,
    InMemoryAuthorityStore,
)


class TestAuthorityDelegation:
    """Test delegation creation and validation."""

    def test_delegation_is_current(self):
        """Test that delegation validity is checked."""
        delegation = AuthorityDelegation(
            delegator_id="alice@bank.com",
            delegator_role="VP of Credit",
            delegatee_id="ai_agent_1",
            scope="credit_approval",
            policy_id="policy_001",
        )
        assert delegation.is_current() is True

    def test_delegation_expired(self):
        """Test that expired delegations are caught."""
        delegation = AuthorityDelegation(
            delegator_id="alice@bank.com",
            delegator_role="VP of Credit",
            delegatee_id="ai_agent_1",
            scope="credit_approval",
            policy_id="policy_001",
            valid_until=_utcnow() - timedelta(days=1),
        )
        assert delegation.is_current() is False

    def test_context_constraint_matching(self):
        """Test that context constraints are enforced."""
        delegation = AuthorityDelegation(
            delegator_id="alice@bank.com",
            delegator_role="VP of Credit",
            delegatee_id="ai_agent_1",
            scope="credit_approval",
            policy_id="policy_001",
            context_constraints={"region": ["US", "EU"], "office": ["HQ"]},
        )

        # Matching context
        assert delegation.matches_context({"region": "US", "office": "HQ"}) is True

        # Non-matching region
        assert delegation.matches_context({"region": "APAC", "office": "HQ"}) is False

        # Non-matching office
        assert delegation.matches_context({"region": "US", "office": "Branch1"}) is False

        # Partial match (only specified constraints are checked)
        assert delegation.matches_context({"region": "US"}) is True


class TestAuthorityGate:
    """Test Authority Gate decision logic."""

    @pytest.fixture
    def gate(self):
        """Create a fresh Authority Gate for each test."""
        return AuthorityGate()

    def test_allow_decision_within_limits(self, gate):
        """Test ALLOW decision for authorized request within limits."""
        gate.create_delegation(
            delegator_id="alice@bank.com",
            delegator_role="VP of Credit",
            delegatee_id="ai_agent_1",
            scope="credit_approval",
            policy_id="policy_001",
            max_value=50000.0,
        )

        request = ExecutionRequest(
            action_id="loan_001",
            action_type="credit_approval",
            actor="ai_agent_1",
            decision_value=30000.0,
        )

        result = gate.check_authority(request)
        assert result.decision == AuthorityDecision.ALLOW
        assert result.delegator == "alice@bank.com"
        assert len(result.violations) == 0
        assert result.proof_hash != ""

    def test_deny_decision_no_delegation(self, gate):
        """Test DENY decision when no delegation exists."""
        request = ExecutionRequest(
            action_id="action_001",
            action_type="nonexistent_scope",
            actor="ai_agent_1",
        )

        result = gate.check_authority(request)
        assert result.decision == AuthorityDecision.DENY
        assert "No active delegation found" in result.reasoning
        assert len(result.violations) > 0

    def test_step_up_decision_exceeds_max_value(self, gate):
        """Test STEP_UP decision when value exceeds limit."""
        gate.create_delegation(
            delegator_id="alice@bank.com",
            delegator_role="VP of Credit",
            delegatee_id="ai_agent_1",
            scope="credit_approval",
            policy_id="policy_001",
            max_value=50000.0,
        )

        request = ExecutionRequest(
            action_id="loan_001",
            action_type="credit_approval",
            actor="ai_agent_1",
            decision_value=75000.0,
        )

        result = gate.check_authority(request)
        assert result.decision == AuthorityDecision.STEP_UP
        assert "exceeds limit" in result.reasoning

    def test_defer_decision_exceeds_max_cost(self, gate):
        """Test DEFER decision when cost exceeds limit."""
        gate.create_delegation(
            delegator_id="alice@bank.com",
            delegator_role="VP of Credit",
            delegatee_id="ai_agent_1",
            scope="credit_approval",
            policy_id="policy_001",
            max_cost=100.0,
        )

        request = ExecutionRequest(
            action_id="loan_001",
            action_type="credit_approval",
            actor="ai_agent_1",
            decision_cost=200.0,
        )

        result = gate.check_authority(request)
        assert result.decision == AuthorityDecision.DEFER

    def test_halt_decision_emergency_threshold(self, gate):
        """Test HALT decision when emergency threshold is exceeded."""
        delegation = AuthorityDelegation(
            delegator_id="alice@bank.com",
            delegator_role="VP of Credit",
            delegatee_id="ai_agent_1",
            scope="credit_approval",
            policy_id="policy_001",
            max_value=1000000.0,
            emergency_escalation_threshold=500000.0,
        )
        gate.store.create_delegation(delegation)

        request = ExecutionRequest(
            action_id="loan_001",
            action_type="credit_approval",
            actor="ai_agent_1",
            decision_value=750000.0,
        )

        result = gate.check_authority(request)
        assert result.decision == AuthorityDecision.HALT
        assert "emergency" in result.reasoning.lower()

    def test_deny_decision_expired_delegation(self, gate):
        """Test DENY decision when delegation has expired."""
        gate.create_delegation(
            delegator_id="alice@bank.com",
            delegator_role="VP of Credit",
            delegatee_id="ai_agent_1",
            scope="credit_approval",
            policy_id="policy_001",
            valid_days=-1,  # Expired yesterday
        )

        request = ExecutionRequest(
            action_id="loan_001",
            action_type="credit_approval",
            actor="ai_agent_1",
        )

        result = gate.check_authority(request)
        assert result.decision == AuthorityDecision.DENY
        assert "expired" in result.reasoning.lower()

    def test_deny_decision_context_violation(self, gate):
        """Test DENY decision when context violates constraints."""
        gate.create_delegation(
            delegator_id="alice@bank.com",
            delegator_role="VP of Credit",
            delegatee_id="ai_agent_1",
            scope="credit_approval",
            policy_id="policy_001",
            context_constraints={"region": ["US", "EU"]},
        )

        request = ExecutionRequest(
            action_id="loan_001",
            action_type="credit_approval",
            actor="ai_agent_1",
            context={"region": "APAC"},
        )

        result = gate.check_authority(request)
        assert result.decision == AuthorityDecision.DENY
        assert "context" in result.reasoning.lower()

    def test_audit_log(self, gate):
        """Test that decisions are logged."""
        gate.create_delegation(
            delegator_id="alice@bank.com",
            delegator_role="VP of Credit",
            delegatee_id="ai_agent_1",
            scope="credit_approval",
            policy_id="policy_001",
        )

        # Make 3 requests
        for i in range(3):
            request = ExecutionRequest(
                action_id=f"loan_{i:03d}",
                action_type="credit_approval",
                actor="ai_agent_1",
                decision_value=10000.0,
            )
            gate.check_authority(request)

        log = gate.get_decision_log()
        assert len(log) == 3
        assert all(r.delegator == "alice@bank.com" for r in log)

    def test_proof_hash_consistency(self, gate):
        """Test that proof hash is consistent for same decision."""
        gate.create_delegation(
            delegator_id="alice@bank.com",
            delegator_role="VP of Credit",
            delegatee_id="ai_agent_1",
            scope="credit_approval",
            policy_id="policy_001",
        )

        request = ExecutionRequest(
            action_id="loan_001",
            action_type="credit_approval",
            actor="ai_agent_1",
            decision_value=10000.0,
        )

        result = gate.check_authority(request)
        assert result.proof_hash != ""
        # Proof should be cryptographically deterministic
        assert len(result.proof_hash) == 64  # SHA256 hex digest


class TestAuthorityStore:
    """Test authority store operations."""

    @pytest.fixture
    def store(self):
        """Create a fresh store for each test."""
        return InMemoryAuthorityStore()

    def test_create_and_retrieve_delegation(self, store):
        """Test creating and retrieving delegations."""
        delegation = AuthorityDelegation(
            delegator_id="alice@bank.com",
            delegator_role="VP of Credit",
            delegatee_id="ai_agent_1",
            scope="credit_approval",
            policy_id="policy_001",
        )

        delegation_id = store.create_delegation(delegation)
        assert delegation_id is not None

        retrieved = store.get_delegation("ai_agent_1", "credit_approval")
        assert retrieved is not None
        assert retrieved.delegator_id == "alice@bank.com"

    def test_revoke_delegation(self, store):
        """Test revoking a delegation."""
        delegation = AuthorityDelegation(
            delegator_id="alice@bank.com",
            delegator_role="VP of Credit",
            delegatee_id="ai_agent_1",
            scope="credit_approval",
            policy_id="policy_001",
        )

        delegation_id = store.create_delegation(delegation)
        store.revoke_delegation(delegation_id)

        retrieved = store.get_delegation("ai_agent_1", "credit_approval")
        assert retrieved is None

    def test_list_active_delegations(self, store):
        """Test listing active delegations for a delegatee."""
        for i in range(3):
            delegation = AuthorityDelegation(
                delegator_id=f"delegator_{i}",
                delegator_role="Manager",
                delegatee_id="ai_agent_1",
                scope=f"scope_{i}",
                policy_id=f"policy_{i}",
            )
            store.create_delegation(delegation)

        delegations = store.list_active_delegations("ai_agent_1")
        assert len(delegations) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
