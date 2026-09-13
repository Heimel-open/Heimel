"""CLI for the model-independent memory governance MVP."""

from __future__ import annotations

import argparse
import json
from typing import Any

from .model_independent_memory_mvp import ActionIntent, MemoryDecisionAction, build_default_mvp


def _print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(description="VALO model-independent memory governance MVP")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("demo", help="Run full model-switch and governance MVP demo")

    extract = sub.add_parser("extract", help="Extract memory candidates from text")
    extract.add_argument("--text", required=True)
    extract.add_argument("--tenant", default="demo")
    extract.add_argument("--owner", default="njal")
    extract.add_argument("--source", default="cli_session")

    compose = sub.add_parser("compose", help="Approve memories and compose context for a model")
    compose.add_argument("--text", required=True)
    compose.add_argument("--task", required=True)
    compose.add_argument("--model", default="qwen_local")
    compose.add_argument("--tenant", default="demo")
    compose.add_argument("--owner", default="njal")

    check = sub.add_parser("check-action", help="Evaluate a proposed tool action")
    check.add_argument("--tool", required=True)
    check.add_argument("--operation", default="run")
    check.add_argument("--risk", default="low")
    check.add_argument("--requires-approval", action="store_true")
    check.add_argument("--tenant", default="demo")
    check.add_argument("--owner", default="njal")

    args = parser.parse_args()
    mvp = build_default_mvp()

    if args.command == "demo":
        _print_json(mvp.run_demo())
        return

    if args.command == "extract":
        candidates = mvp.extractor.extract(args.text, args.tenant, args.owner, args.source)
        _print_json([candidate.model_dump(mode="json") for candidate in candidates])
        return

    if args.command == "compose":
        candidates = mvp.extractor.extract(args.text, args.tenant, args.owner, "cli_session")
        for candidate in candidates:
            mvp.memory_gate.decide(candidate, force=MemoryDecisionAction.REMEMBER)
        context = mvp.context_composer.compose(
            tenant=args.tenant,
            owner=args.owner,
            task=args.task,
            role="architect",
            risk="medium",
            model=args.model,
        )
        _print_json(context.model_dump(mode="json"))
        return

    if args.command == "check-action":
        decision = mvp.execution_governance.evaluate(
            ActionIntent(
                tenant=args.tenant,
                owner=args.owner,
                tool=args.tool,
                operation=args.operation,
                risk=args.risk,
                requires_approval=args.requires_approval,
            )
        )
        _print_json(decision.model_dump(mode="json"))
        return


if __name__ == "__main__":
    main()
