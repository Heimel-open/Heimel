"""Command line entry point for the local relAIon node."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from paios.node import DEFAULT_NODE_NAME, RelAIonNode


def _state_dir() -> Path:
    return Path(os.environ.get("RELAION_STATE_DIR", "~/.local/share/relaion/alpha")).expanduser()


def main() -> int:
    parser = argparse.ArgumentParser(prog="relaion")
    parser.add_argument("command", choices=("init", "health", "identity"))
    parser.add_argument("--node", default=os.environ.get("RELAION_NODE_NAME", DEFAULT_NODE_NAME))
    parser.add_argument("--state-dir", type=Path, default=_state_dir())
    args = parser.parse_args()

    node = RelAIonNode(args.state_dir, args.node)
    if args.command == "init":
        print(json.dumps({"ok": True, "node": node.identity.node_name, "state_dir": str(node.state_dir)}))
    elif args.command == "health":
        print(json.dumps(node.health(), sort_keys=True))
    else:
        print(json.dumps(node.identity.__dict__, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
