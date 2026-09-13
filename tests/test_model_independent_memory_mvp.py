from src.valo_platform.model_independent_memory_mvp import (
    ActionIntent,
    ExecutionDecisionAction,
    MemoryDecisionAction,
    build_default_mvp,
)


def test_learning_extractor_creates_candidates():
    mvp = build_default_mvp()
    candidates = mvp.extractor.extract(
        "Remember that memory must survive model changes. Preference: use local models for drafts.",
        tenant="demo",
        owner="njal",
        source="test_session",
    )

    assert len(candidates) == 2
    assert {candidate.type for candidate in candidates} == {"fact", "preference"}


def test_memory_gate_stores_approved_memory_and_writes_receipt():
    mvp = build_default_mvp()
    candidate = mvp.extractor.extract(
        "Decision: all model switches must preserve canonical memory.",
        tenant="demo",
        owner="njal",
        source="test_session",
    )[0]

    decision = mvp.memory_gate.decide(candidate, force=MemoryDecisionAction.REMEMBER)

    assert decision.action == MemoryDecisionAction.REMEMBER
    assert len(mvp.store.list()) == 1
    assert len(mvp.receipts.list()) == 1
    assert mvp.receipts.list()[0].event_type == "memory_decision"


def test_context_composer_uses_minimal_governed_memory():
    mvp = build_default_mvp()
    for text in [
        "Fact: VALO memory is model independent.",
        "Preference: use Qwen locally for low risk tasks.",
        "Decision: external messages require governance.",
    ]:
        candidate = mvp.extractor.extract(text, "demo", "njal", "test_session")[0]
        mvp.memory_gate.decide(candidate, force=MemoryDecisionAction.REMEMBER)

    context = mvp.context_composer.compose(
        tenant="demo",
        owner="njal",
        task="continue model independent memory work",
        role="architect",
        risk="medium",
        model="qwen_local",
        max_items=2,
    )

    assert context.model == "qwen_local"
    assert len(context.memory_ids) == 2
    assert "no_execution_without_governance" in context.constraints


def test_model_switch_preserves_context_package():
    mvp = build_default_mvp()
    candidate = mvp.extractor.extract(
        "Fact: governed memory survives when Qwen is replaced by Claude.",
        tenant="demo",
        owner="njal",
        source="test_session",
    )[0]
    mvp.memory_gate.decide(candidate, force=MemoryDecisionAction.REMEMBER)
    context = mvp.context_composer.compose(
        tenant="demo",
        owner="njal",
        task="continue Qwen to Claude work",
        role="architect",
        risk="medium",
        model="qwen_local",
    )

    result = mvp.model_router.switch_model("qwen_local", "claude_api", context)

    assert "claude_api" in result
    assert context.memory_ids
    assert any(receipt.event_type == "model_switch" for receipt in mvp.receipts.list())


def test_execution_governance_steps_up_sensitive_action():
    mvp = build_default_mvp()
    decision = mvp.execution_governance.evaluate(
        ActionIntent(
            tenant="demo",
            owner="njal",
            tool="email.send",
            operation="send_external_message",
            risk="medium",
            requires_approval=True,
        )
    )

    assert decision.action == ExecutionDecisionAction.STEP_UP
    assert decision.receipt_id is not None


def test_full_demo_flow():
    mvp = build_default_mvp()
    result = mvp.run_demo()

    assert result["candidates"]
    assert result["memory_decisions"]
    assert result["stored_memories"]
    assert result["context_package"]["memory_ids"]
    assert "qwen_local" in result["qwen_result"]
    assert "claude_api" in result["claude_result"]
    assert result["execution_decision"]["action"] == "STEP_UP"
    assert result["receipts"]
