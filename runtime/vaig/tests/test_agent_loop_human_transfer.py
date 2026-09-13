from vaig.agent_loop import AgentLoop, LoopStep


def test_denied_authority_mismatch_returns_human_transfer_object():
    loop = AgentLoop(original_intent="Summarize a repository file")
    result = loop.run(
        [
            LoopStep(
                event_type="tool_call",
                current_frame="Update repository file",
                proposed_action="update file",
                tool="github.update_file",
                tool_authority="write",
                task_authority="read",
            )
        ]
    )

    transfer = result.receipt["human_transfer"]

    assert result.halted is True
    assert result.decisions[-1].decision == "deny"
    assert transfer["required"] is True
    assert transfer["why"] == "tool authority exceeds task authority"
    assert "read-only" in transfer["remaining_uncertainty"]
    assert "sufficient authority" in transfer["standing_to_act"]
    assert "stop execution" in transfer["available_options"]
    assert "re-scope to an allowed lower-authority action" in transfer["available_options"]
    assert transfer["accountability_path"] == "receipt -> operator review -> scoped authorization or halt"


def test_fast_path_does_not_require_human_transfer():
    loop = AgentLoop(original_intent="Read a repository file")
    result = loop.run(
        [
            LoopStep(
                event_type="tool_call",
                current_frame="Read repository file",
                proposed_action="read file",
                tool="github.fetch_file",
                tool_authority="read",
                task_authority="read",
                uncertainty=0.01,
                drift_score=0.01,
            )
        ]
    )

    transfer = result.receipt["human_transfer"]

    assert result.halted is False
    assert result.decisions[-1].decision == "allow_fast"
    assert transfer["required"] is False
    assert transfer["available_options"] == []
