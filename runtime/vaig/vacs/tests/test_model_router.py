from vacs.src.model_router import (
    RouteDecision,
    TaskProfile,
    VALOModelRouter,
    default_model_registry,
)


def test_routes_low_risk_internal_work_to_local_model():
    router = VALOModelRouter()
    task = TaskProfile(
        task_id="summarize-local-context",
        task_type="summary",
        input_tokens=4_000,
        expected_output_tokens=500,
        required_quality=0.70,
        required_reasoning=0.50,
        data_class="internal",
        risk_level="low",
    )

    result = router.route(task, default_model_registry())

    assert result.decision == RouteDecision.LOCAL
    assert result.selected_model.model_id == "ollama-small-local"
    assert result.estimated_cost_usd == 0.0


def test_sensitive_personal_data_does_not_route_to_remote():
    router = VALOModelRouter()
    task = TaskProfile(
        task_id="personal-data-extract",
        task_type="data_extraction",
        input_tokens=10_000,
        expected_output_tokens=1_000,
        required_quality=0.78,
        required_reasoning=0.65,
        data_class="personal",
        risk_level="medium",
        requires_tools=True,
    )

    result = router.route(task, default_model_registry())

    assert result.selected_model.endpoint_type == "private"
    assert result.selected_model.model_id == "private-mid"
    assert result.decision == RouteDecision.REMOTE


def test_remote_frontier_only_when_capability_required():
    router = VALOModelRouter()
    task = TaskProfile(
        task_id="remote-market-research",
        task_type="research",
        input_tokens=20_000,
        expected_output_tokens=3_000,
        required_quality=0.90,
        required_reasoning=0.90,
        data_class="public",
        risk_level="medium",
        requires_tools=True,
        requires_remote_knowledge=True,
    )

    result = router.route(task, default_model_registry())

    assert result.decision == RouteDecision.REMOTE
    assert result.selected_model.model_id == "remote-strong"
    assert result.estimated_cost_usd > 0


def test_high_risk_task_requires_human_after_model_selection():
    router = VALOModelRouter()
    task = TaskProfile(
        task_id="regulated-decision-support",
        task_type="analysis",
        input_tokens=12_000,
        expected_output_tokens=2_000,
        required_quality=0.78,
        required_reasoning=0.65,
        data_class="internal",
        risk_level="high",
        requires_tools=True,
    )

    result = router.route(task, default_model_registry())

    assert result.decision == RouteDecision.HUMAN
    assert result.selected_model is not None


def test_secret_data_never_routes_to_remote():
    router = VALOModelRouter()
    task = TaskProfile(
        task_id="secret-board-note",
        task_type="summary",
        input_tokens=2_000,
        expected_output_tokens=300,
        required_quality=0.65,
        required_reasoning=0.45,
        data_class="secret",
        risk_level="low",
    )

    result = router.route(task, default_model_registry())

    assert result.decision == RouteDecision.LOCAL
    assert result.selected_model.provider == "ollama"


def test_receipt_records_routing_decision():
    router = VALOModelRouter()
    task = TaskProfile(
        task_id="summarize-local-context",
        task_type="summary",
        input_tokens=4_000,
        expected_output_tokens=500,
        data_class="internal",
    )

    result = router.route(task, default_model_registry())
    receipt = router.receipt(result)

    assert receipt["type"] == "valo.model_router.receipt.v1"
    assert receipt["decision"] == "LOCAL"
    assert receipt["selected_model_id"] == "ollama-small-local"
    assert receipt["payload_hash"].startswith("sha256:")
