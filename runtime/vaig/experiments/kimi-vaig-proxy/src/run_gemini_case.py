from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from gemini_client import call_gemini_direct, call_gemini_filtered
from vaig_filter import evaluate_case


def load_case(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_log(entry: dict[str, Any]) -> None:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    with (log_dir / "results.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a case through the VAIG-style Gemini proxy.")
    parser.add_argument("case_path", help="Path to case JSON file")
    parser.add_argument("--direct", action="store_true", help="Send directly to Gemini without governance filter")
    parser.add_argument("--no-model", action="store_true", help="Evaluate governance only; do not call Gemini")
    args = parser.parse_args()

    case = load_case(args.case_path)
    governance = evaluate_case(case)

    entry: dict[str, Any] = {
        "timestamp": dt.datetime.now(dt.UTC).isoformat(),
        "case_name": case.get("case_name"),
        "provider": "gemini",
        "test_type": "direct_gemini" if args.direct else "vaig_style_proxy",
        "runtime_status": "prototype_harness_not_full_valo_runtime",
        "governance": governance.to_dict(),
        "model_called": False,
        "filtered": not args.direct,
        "model_output": None,
    }

    if args.no_model:
        entry["test_type"] = "governance_only"
    elif args.direct:
        entry["model_called"] = True
        entry["model_output"] = call_gemini_direct(case)
    elif governance.llm_allowed:
        entry["model_called"] = True
        entry["model_output"] = call_gemini_filtered(case, governance)

    write_log(entry)
    print(json.dumps(entry, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
