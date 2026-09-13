from vaig.agent_loop import AgentLoop, LoopStep


def test_write_authority_low_risk_resolves_to_allow():
    # External-effect authority is an execution-layer concern, not a verdict.
    # Low-risk reversible write with matching task authority -> ALLOW.
    loop = AgentLoop(original_intent="Read a file")
    result = loop.run(
        [
            LoopStep(
                event_type="tool_call",
                current_frame="Modify a file",
                proposed_action="update file",
                tool="github.update_file",
                tool_authority="write",
                task_authority="write",
                reversibility="partially_reversible",
            )
        ]
    )

    assert result.decisions[-1].decision == "slow_path"


def test_delete_authority_exceeding_task_scope_is_denied():
    loop = AgentLoop(original_intent="Read a file")
    result = loop.run(
        [
            LoopStep(
                event_type="tool_call",
                current_frame="Delete a file",
                proposed_action="delete file",
                tool="github.delete_file",
                tool_authority="delete",
                task_authority="read",
            )
        ]
    )

    assert result.halted is True
    assert result.decisions[-1].decision == "deny"
    assert "authority exceeds" in result.decisions[-1].reason
