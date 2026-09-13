from __future__ import annotations

import argparse
import json

from . import __all__


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect the public VALO contract SDK")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="List exported public contract types")
    args = parser.parse_args()
    if args.command == "list":
        print(json.dumps({"contracts": sorted(__all__), "network": False, "authority": False}, indent=2))


if __name__ == "__main__":
    main()
