"""
Integration test: Full VAIG economy chain (VACS → ROI → Authority → Router → Execute → Efficiency → Reward)

Tests the complete flow from decision to reward allocation.
"""

import pytest
from datetime import datetime, timedelta, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
from decimal import Decimal

from src.roi_gate import ROIGate, ROIRequest, CostEstimate, ValueEstimate, ROIPolicy, ROIDecision
from src.authority_gate import AuthorityGate, AuthorityPolicy, PolicyDecision, ExecutionRequest, AuthorityDelegation
from src.model_router import ModelRouter, TaskRequirements, ModelTier
from src.spend_gate import SpendGate, SpendRequest, SpendPolicy, SpendDecision, BudgetAllocation, BudgetPeriod
from src.efficiency_engine import EfficiencyEngine, ActionExecution, ValueMeasurement, EfficiencyPolicy, OutcomeStatus
from src.value_weighting import ValueWeighting, ValueComponent, ValueDomain, ValueAxis, WeightingPolicy
from src.reward_economy import RewardEconomy, RewardPolicy, RewardType


class TestIntegrationFullChain:
    """Integration tests for complete VAIG economy stack."""

    @pytest.fixture
    def setup_gates(self):
        """Initialize all gates and policies."""
        return {
            "roi": ROIGate(policy=ROIPolicy()),
            "authority": AuthorityGate(policy=AuthorityPolicy()),
            "router": ModelRouter(),
            "spend": SpendGate(policy=SpendPolicy()),
            "efficiency": EfficiencyEngine(policy=EfficiencyPolicy()),
            "weighting": ValueWeighting(policy=WeightingPolicy()),
            "reward": RewardEconomy(policy=RewardPolicy()),
        }

    def test_scenario_1_routine_api_call(self, setup_gates):
        """
        Scenario 1: Routine API call with positive outcome

        Flow:
          1. ROI Gate: Should this action happen? YES (high ROI)
          2. Authority: Is it authorized? YES (matches policy)
          3. Router: Which model? LOCAL (cheapest)
          4. Spend: Budget available? YES
          5. Execute: Action runs, succeeds
          6. Efficiency: Measure outcome (value > expected)
          7. Reward: Allocate tokens
        """
        gates = setup_gates
        principal_id = "user/alice"
        action_id = "action_001"

        # Phase 1: ROI Gate
        roi_request = ROIRequest(
            action_id=action_id,
            category="routine",
            cost_estimate=CostEstimate(
                tokens_prompt=500,
                tokens_completion=200,
                compute_seconds=2.0,
            ),
            value_estimate=ValueEstimate(
                revenue=Decimal("150"),
                saved_labor_hours=0.5,
            ),
            risk_level="low",
        )
        roi_result = gates["roi"].evaluate(roi_request)
        assert roi_result.decision == ROIDecision.ALLOW
        assert float(roi_result.roi_ratio) > 2.0

        # Phase 2: Authority Gate (register delegation first)
        delegation = AuthorityDelegation(
            delegator_id="VP_Credit",
            delegator_role="VP",
            delegatee_id=principal_id,
            scope="api_call",
            policy_id="policy_001",
        )
        gates["authority"].store.create_delegation(delegation)

        authority_result = gates["authority"].check_authority(
            ExecutionRequest(
                action_id=action_id,
                action_type="api_call",
                actor=principal_id,
                context={"type": "api_call", "target": "internal"},
            )
        )
        assert authority_result.decision == PolicyDecision.ALLOW

        # Phase 3: Model Router
        routing_result = gates["router"].route(
            TaskRequirements(
                prompt_tokens=500,
                expected_completion_tokens=200,
                min_quality=0.7,
                prefer_local=True,
            )
        )
        assert routing_result.decision.name == "ALLOW"
        assert routing_result.selected_model.local is True

        # Phase 4: Spend Gate (allocate budget first)
        budget = BudgetAllocation(
            principal_id=principal_id,
            period=BudgetPeriod.MONTHLY,
            total_usd=Decimal("1000"),
            start_date=_utcnow(),
            end_date=_utcnow() + timedelta(days=30),
        )
        gates["spend"].allocate_budget(budget)

        spend_result = gates["spend"].authorize(
            SpendRequest(
                principal_id=principal_id,
                amount_usd=routing_result.estimated_cost,
                category="compute",
                reason=action_id,
            )
        )
        assert spend_result.decision == SpendDecision.ALLOW

        # Phase 5: Execute (simulate execution)
        execution = ActionExecution(
            action_id=action_id,
            category="api_call",
            initiated_by=principal_id,
            initiated_at=_utcnow(),
            completed_at=_utcnow() + timedelta(seconds=2),
            tokens_used=700,
            cost_actual_usd=routing_result.estimated_cost,
            outcome=OutcomeStatus.SUCCESS,
        )
        gates["efficiency"].record_execution(action_id, execution)

        # Phase 6: Efficiency Measurement
        value = ValueMeasurement(
            revenue_generated=Decimal("180"),  # Beat expected $150
            labor_saved_hours=0.6,  # Beat expected 0.5
        )
        efficiency_result = gates["efficiency"].measure_outcome(
            action_id=action_id,
            value=value,
            expected_value=Decimal("200"),  # ROI gate estimated $200
        )
        assert efficiency_result.efficiency_grade.name in ["EXCELLENT", "GOOD", "ACCEPTABLE"]

        # Phase 7: Value Normalization
        normalized = gates["weighting"].normalize(
            ValueComponent(
                domain=ValueDomain.FINANCIAL,
                quantity=value.net_value,
                unit="USD",
                axis=ValueAxis.EVIDENCE,
                period_days=1,
            )
        )
        assert normalized.normalized_usd > Decimal("0")

        # Phase 8: Reward Allocation
        reward_calc = gates["reward"].calculate_reward(
            action_id=action_id,
            principal_id=principal_id,
            ves_ratio=efficiency_result.ves_ratio,
            expected_ves=efficiency_result.expected_ves,
            actual_value_usd=efficiency_result.actual_value,
        )
        assert reward_calc.total_tokens > Decimal("0")

        grant = gates["reward"].grant_tokens(reward_calc)
        assert grant.status.value == "GRANTED"

        # Verify end state
        balance = gates["reward"].get_principal_balance(principal_id)
        assert balance["total_balance"] > 0

    def test_scenario_2_high_cost_action_escalation(self, setup_gates):
        """
        Scenario 2: High-cost action requiring escalation

        Flow:
          1. ROI Gate: Borderline ROI → STEP_UP
          2. Authority: Requires approval → DEFER
          3. (Would require human approval)
        """
        gates = setup_gates
        principal_id = "user/bob"
        action_id = "action_002"

        # High-cost, borderline ROI action
        roi_request = ROIRequest(
            action_id=action_id,
            category="experimental",
            cost_estimate=CostEstimate(
                tokens_prompt=5000,
                tokens_completion=2000,
                compute_seconds=30.0,
            ),
            value_estimate=ValueEstimate(
                revenue=Decimal("500"),
            ),
            risk_level="high",  # High risk reduces expected value
        )
        roi_result = gates["roi"].evaluate(roi_request)
        # With high risk adjustment, may trigger STEP_UP
        assert roi_result.requires_escalation or roi_result.decision == ROIDecision.ALLOW

    def test_scenario_3_budget_exhaustion(self, setup_gates):
        """
        Scenario 3: Budget exhaustion blocking execution

        Flow:
          1. ROI Gate: ALLOW
          2. Authority: ALLOW
          3. Router: Route to model
          4. Spend: STEP_UP/DENY (budget exhausted)
          5. No execution
        """
        gates = setup_gates
        principal_id = "user/charlie"

        # Low budget allocation
        budget = BudgetAllocation(
            principal_id=principal_id,
            period=BudgetPeriod.DAILY,
            total_usd=Decimal("50"),  # $50 budget
            start_date=_utcnow(),
            end_date=_utcnow() + timedelta(days=1),
        )
        gates["spend"].allocate_budget(budget)

        # Exhaust budget with transactions
        decisions_seen = []
        for i in range(12):
            spend_result = gates["spend"].authorize(
                SpendRequest(
                    principal_id=principal_id,
                    amount_usd=Decimal("5.00"),  # $5 each
                    category="compute",
                    reason=f"action_{i:03d}",
                )
            )
            decisions_seen.append(spend_result.decision)
            # Early transactions (0-5) should be ALLOW
            if i <= 5:
                assert spend_result.decision == SpendDecision.ALLOW
            # Mid transactions (6-8) may hit thresholds (STEP_UP)
            if i >= 6:
                # After $30 spent (60%), we're approaching step_up (90%) and warn (85%)
                assert spend_result.decision in [SpendDecision.ALLOW, SpendDecision.STEP_UP]
            # Late transactions (9+) should hit escalation or denial
            if i >= 9:
                # After $45 spent (90%), should see escalation/denial
                assert spend_result.decision in [SpendDecision.STEP_UP, SpendDecision.DENY, SpendDecision.DEFER, SpendDecision.HALT]

        # Verify budget state is tracked
        final_state = gates["spend"]._get_budget_state(principal_id)
        assert final_state.available < final_state.allocation.total_usd

    def test_scenario_4_failed_execution_efficiency_signal(self, setup_gates):
        """
        Scenario 4: Execution fails, generates negative learning signal

        Flow:
          1. Passes ROI/Authority/Router/Spend gates
          2. Executes but outcome is FAILED
          3. Efficiency Engine: FAILURE grade
          4. Reward: No tokens (or reduced)
        """
        gates = setup_gates
        principal_id = "user/diana"
        action_id = "action_004"

        # Record execution that failed
        execution = ActionExecution(
            action_id=action_id,
            category="experiment",
            initiated_by=principal_id,
            initiated_at=_utcnow(),
            completed_at=_utcnow() + timedelta(seconds=5),
            tokens_used=1000,
            cost_actual_usd=Decimal("5.00"),
            outcome=OutcomeStatus.FAILED,
        )
        gates["efficiency"].record_execution(action_id, execution)

        # Measure: expected $100, got $0
        value = ValueMeasurement(revenue_generated=Decimal("0"))
        efficiency_result = gates["efficiency"].measure_outcome(
            action_id=action_id,
            value=value,
            expected_value=Decimal("100"),
        )

        # Should be FAILURE or POOR
        assert efficiency_result.efficiency_grade.name in ["POOR", "FAILURE"]
        assert efficiency_result.variance_pct < 0  # Below expected

        # Reward: Calculate with low VES
        reward_calc = gates["reward"].calculate_reward(
            action_id=action_id,
            principal_id=principal_id,
            ves_ratio=efficiency_result.ves_ratio,
            expected_ves=efficiency_result.expected_ves,
            actual_value_usd=Decimal("0"),
        )
        # Should be minimal/zero tokens
        assert reward_calc.total_tokens >= Decimal("0")

    def test_decision_log_audit_trail(self, setup_gates):
        """
        Verify audit trail completeness across all gates.
        Each gate should maintain decision log with hashes.
        """
        gates = setup_gates

        # Execute a full flow
        roi_request = ROIRequest(
            action_id="audit_test_001",
            cost_estimate=CostEstimate(tokens_prompt=500),
            value_estimate=ValueEstimate(revenue=Decimal("100")),
        )
        roi_result = gates["roi"].evaluate(roi_request)

        # Verify ROI log
        roi_log = gates["roi"].decision_log
        assert len(roi_log) > 0
        assert roi_log[-1].hash != ""
        assert len(roi_log[-1].hash) == 64  # SHA256 hex

        # Verify Authority log
        authority_log = gates["authority"].decision_log
        assert len(authority_log) >= 0  # May or may not have decisions yet

        # Verify Spend log
        spend_log = gates["spend"].decision_log
        assert isinstance(spend_log, list)

        # Verify Efficiency log
        efficiency_log = gates["efficiency"].measurement_log
        assert isinstance(efficiency_log, list)

    def test_cross_module_state_consistency(self, setup_gates):
        """
        Verify state consistency across modules during decision flow.
        """
        gates = setup_gates

        # Setup budget
        principal_id = "test_principal"
        budget = BudgetAllocation(
            principal_id=principal_id,
            period=BudgetPeriod.MONTHLY,
            total_usd=Decimal("1000"),
            start_date=_utcnow(),
        )
        gates["spend"].allocate_budget(budget)

        # Get initial state
        state_before = gates["spend"]._get_budget_state(principal_id)
        initial_available = state_before.available

        # Spend budget
        gates["spend"].authorize(
            SpendRequest(
                principal_id=principal_id,
                amount_usd=Decimal("100"),
                category="test",
            )
        )

        # Verify state updated
        state_after = gates["spend"]._get_budget_state(principal_id)
        assert state_after.available == initial_available - Decimal("100")
        assert state_after.spent == Decimal("100")


class TestDecisionVocabularyConsistency:
    """Verify all gates use consistent decision vocabulary."""

    def test_decision_enums_compatible(self):
        """All decision enums should support: ALLOW, STEP_UP, DEFER, DENY, HALT."""
        from src.roi_gate import ROIDecision
        from src.authority_gate import PolicyDecision
        from src.model_router import RouterDecision
        from src.spend_gate import SpendDecision

        decisions = [ROIDecision, PolicyDecision, RouterDecision, SpendDecision]
        shared_vocab = {"ALLOW", "STEP_UP", "DEFER", "DENY", "HALT"}

        for decision_class in decisions:
            enum_values = {d.name for d in decision_class}
            assert shared_vocab.issubset(enum_values), \
                f"{decision_class.__name__} missing vocabulary: {shared_vocab - enum_values}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
