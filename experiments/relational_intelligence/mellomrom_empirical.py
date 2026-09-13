#!/usr/bin/env python3
"""Strict empirical gate for MELLOMROM relational-lineage runs.

The generic control builder can operate on any episode-shaped records. This
wrapper is stricter: empirical RUN-001 packs may only be built from raw source
episodes. Derived summaries, quoted analysis, reconstructed anchors and model-
generated episode surrogates must fail closed.
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Mapping, Sequence

from experiments.relational_intelligence.mellomrom_lineage import build_control_pack

Episode = Mapping[str, Any]

REQUIRED_RAW_FIELDS = (
    "episode_id",
    "chat_id",
    "context_before",
    "assistant_output",
    "human_correction",
)


def validate_raw_episodes(episodes: Sequence[Episode]) -> None:
    if len(episodes) < 4:
        raise ValueError("at least four raw episodes are required")

    for index, episode in enumerate(episodes):
        provenance = str(episode.get("provenance", ""))
        if provenance != "raw":
            raise ValueError(
                f"episode {index} provenance must be 'raw'; got {provenance!r}"
            )

        for field in REQUIRED_RAW_FIELDS:
            value = episode.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                raise ValueError(f"episode {index} missing required raw field {field!r}")


def build_empirical_control_pack(episodes: Sequence[Episode]) -> dict[str, Any]:
    """Build a lineage-control pack only after raw-source validation."""

    validate_raw_episodes(episodes)
    pack = build_control_pack(episodes)
    pack["evidence_class"] = "RAW_EMPIRICAL_SOURCE"
    pack["empirical_gate"] = "RAW_PROVENANCE_REQUIRED"
    return pack


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("episodes", help="JSON list of raw MELLOMROM episodes")
    parser.add_argument("output", help="output empirical control-pack JSON")
    args = parser.parse_args()

    with open(args.episodes, "r", encoding="utf-8") as handle:
        episodes = json.load(handle)
    if not isinstance(episodes, list):
        raise ValueError("episodes input must be a JSON list")

    pack = build_empirical_control_pack(episodes)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(pack, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
