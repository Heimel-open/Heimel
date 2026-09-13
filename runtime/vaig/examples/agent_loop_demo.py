from vaig.agent_loop import AgentLoop, LoopStep


def main() -> None:
    loop = AgentLoop(original_intent="Summarize a repository file")
    result = loop.run(
        [
            LoopStep(
                event_type="input",
                current_frame="Summarize a repository file",
                task_authority="read",
            ),
            LoopStep(
                event_type="tool_call",
                current_frame="Read repository file",
                proposed_action="fetch README.md",
                tool="github.fetch_file",
                tool_authority="read",
                task_authority="read",
            ),
            LoopStep(
                event_type="action",
                current_frame="Update repository file",
                proposed_action="write modified README.md",
                tool="github.update_file",
                tool_authority="write",
                task_authority="read",
            ),
        ]
    )

    for decision in result.decisions:
        print(f"{decision.decision}: {decision.reason}")
    print(result.receipt)


if __name__ == "__main__":
    main()
