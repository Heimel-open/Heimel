from vacs.src.exploration_budget import (
    BudgetDecision,
    BudgetWallet,
    ExplorationRequest,
    SpendClass,
    VALOExplorationBudgetGate,
)


def wallet():
    return BudgetWallet(
        wallet_id="wallet_001",
        owner_id="employee_001",
        period="2026-W26",
        total_budget_usd=25.0,
        used_budget_usd=5.0,
        local_token_budget=1_000_000,
        used_local_tokens=100_000,
        remote_token_budget=100_000,
        used_remote_tokens=10_000,
        frontier_call_budget=2,
        used_frontier_calls=0,
    )


def test_allows_low_risk_play_inside_budget():
    gate = VALOExplorationBudgetGate()
    request = ExplorationRequest(
        request_id="play_001",
        spend_class=SpendClass.PLAY,
        estimated_cost_usd=0.10,
        estimated_local_tokens=20_000,
        risk_level="low",
        data_class="internal",
        expected_learning="test whether local model can draft rough ideas",
    )

    result = gate.evaluate(request, wallet())

    assert result.decision == BudgetDecision.ALLOW
    assert "bounded exploration" in result.reason


def test_production_work_defers_to_roi_gate():
    gate = VALOExplorationBudgetGate()
    request = ExplorationRequest(
        request_id="prod_001",
        spend_class=SpendClass.PRODUCTION,
        estimated_cost_usd=1.00,
        estimated_remote_tokens=5_000,
        risk_level="low",
        data_class="internal",
        expected_learning="n/a",
    )

    result = gate.evaluate(request, wallet())

    assert result.decision == BudgetDecision.DEFER
    assert "ROI Gate" in result.reason


def test_blocks_secret_data_for_exploration():
    gate = VALOExplorationBudgetGate()
    request = ExplorationRequest(
        request_id="secret_001",
        spend_class=SpendClass.EXPERIMENT,
        estimated_cost_usd=0.20,
        estimated_local_tokens=5_000,
        risk_level="low",
        data_class="secret",
        expected_learning="try a prompt pattern",
    )

    result = gate.evaluate(request, wallet())

    assert result.decision == BudgetDecision.DENY


def test_personal_data_requires_step_up():
    gate = VALOExplorationBudgetGate()
    request = ExplorationRequest(
        request_id="personal_001",
        spend_class=SpendClass.LEARNING,
        estimated_cost_usd=0.20,
        estimated_local_tokens=5_000,
        risk_level="low",
        data_class="personal",
        expected_learning="learn extraction format",
    )

    result = gate.evaluate(request, wallet())

    assert result.decision == BudgetDecision.STEP_UP


def test_frontier_model_requires_step_up_even_inside_budget():
    gate = VALOExplorationBudgetGate()
    request = ExplorationRequest(
        request_id="frontier_001",
        spend_class=SpendClass.EXPERIMENT,
        estimated_cost_usd=2.00,
        estimated_remote_tokens=2_000,
        uses_frontier_model=True,
        risk_level="low",
        data_class="public",
        expected_learning="compare frontier quality against local baseline",
    )

    result = gate.evaluate(request, wallet())

    assert result.decision == BudgetDecision.STEP_UP
    assert "frontier" in result.reason


def test_requires_learning_capture():
    gate = VALOExplorationBudgetGate()
    request = ExplorationRequest(
        request_id="empty_learning_001",
        spend_class=SpendClass.PLAY,
        estimated_cost_usd=0.10,
        estimated_local_tokens=2_000,
        risk_level="low",
        data_class="internal",
        expected_learning="",
    )

    result = gate.evaluate(request, wallet())

    assert result.decision == BudgetDecision.DEFER


def test_external_action_requires_step_up():
    gate = VALOExplorationBudgetGate()
    request = ExplorationRequest(
        request_id="external_001",
        spend_class=SpendClass.EXPERIMENT,
        estimated_cost_usd=0.10,
        estimated_local_tokens=2_000,
        risk_level="low",
        data_class="internal",
        external_action=True,
        expected_learning="test whether workflow handoff is useful",
    )

    result = gate.evaluate(request, wallet())

    assert result.decision == BudgetDecision.STEP_UP


def test_receipt_contains_budget_fields():
    gate = VALOExplorationBudgetGate()
    request = ExplorationRequest(
        request_id="play_001",
        spend_class=SpendClass.PLAY,
        estimated_cost_usd=0.10,
        estimated_local_tokens=20_000,
        risk_level="low",
        data_class="internal",
        expected_learning="test local model ideation",
    )

    result = gate.evaluate(request, wallet())
    receipt = gate.receipt(result)

    assert receipt["type"] == "valo.exploration_budget.receipt.v1"
    assert receipt["decision"] == "ALLOW"
    assert receipt["spend_class"] == "play"
    assert receipt["payload_hash"].startswith("sha256:")
