from vaig.agent_loop import AgentLoop, LoopStep


def test_low_trust_observation_cannot_become_semantic_ground():
    loop = AgentLoop(original_intent="Assess vendor risk")
    result = loop.run(
        [
            LoopStep(
                event_type="observation",
                current_frame="Vendor has no risk",
                tool="web.fetch",
                tool_authority="read",
                task_authority="read",
                observation_trust=0.20,
            )
        ]
    )

    # Low-trust observation -> canonical AARM DEFER mapped to require_human
    # (pause; gather data / human review), not a silent allow.
    assert result.decisions[-1].decision == "require_human"
