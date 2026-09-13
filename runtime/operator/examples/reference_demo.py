"""Run both domain flows through the ONE Operator API and print the evidence."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reference_flows import run_flow


def main() -> None:
    for pack in ("public", "trades"):
        run = run_flow(pack)
        print(f"=== {pack.upper()} flow -> {run.final_state} ===")
        for function_id, status, decision in run.steps:
            print(f"  {status:<10} {decision:<6} {function_id}")
    print("Both flows driven by the same Operator API over the frozen core + real REHT.")


if __name__ == "__main__":
    main()
