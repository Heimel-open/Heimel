from __future__ import annotations

import argparse
import json

from . import __all__
from .demo import run_demo


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect the public VALO contract SDK")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="List exported public contract types")
    sub.add_parser("demo", help="Run the offline public contract chain")
    args = parser.parse_args()
    if args.command == "list":
        print(json.dumps({"contracts": sorted(__all__), "network": False, "authority": False}, indent=2))
    if args.command == "demo":
        print(json.dumps(run_demo(), indent=2, default=str))


if __name__ == "__main__":
    main()
