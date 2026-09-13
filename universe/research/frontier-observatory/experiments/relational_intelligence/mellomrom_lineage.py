#!/usr/bin/env python3
"""MELLOMROM bridge for long-horizon relational-intelligence ablations.

This module turns a frozen sequence of human-AI correction episodes into
information-volume-matched lineage conditions for blinded downstream scoring.
It does not score intelligence from transcript style or complexity.

Expected episode fields follow experiments/mellomrom/mellomrom_v0_1_schema.json.
The important intervention is ordering/lineage: the same episodes and endpoints
are preserved while the interior relational history is changed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from statistics import mean
from typing import Any, Mapping, Sequence

Episode = Mapping[str, Any]

CANONICAL_FIELDS = (
    "episode_id",
    "chat_id",
    "timestamp",
    "context_before",
    "assistant_output",
    "human_correction",
    "assistant_repair",
    "later_validation",
    "error_labels",
    "lost_reference",
    "correction_delta",
    "ground_truth_type",
    "accepted_after_repair",
    "recurs_later",
    "provenance",
    "confidence",
)


@dataclass(frozen=True)
class LineageScore:
    intact: float
    shuffled: float
    endpoint_matched: float

    @property
    def history_gain(self) -> float:
        return self.intact - self.shuffled

    @property
    def lineage_specificity(self) -> float:
        return self.intact - self.endpoint_matched

    def candidate_signature(
        self,
        *,
        min_intact: float = 0.70,
        min_gain: float = 0.10,
    ) -> bool:
        return (
            self.intact >= min_intact
            and self.history_gain >= min_gain
            and self.lineage_specificity >= min_gain
        )


def _episode_id(episode: Episode) -> str:
    episode_id = str(episode.get("episode_id", ""))
    if not episode_id:
        raise ValueError("every episode requires episode_id")
    return episode_id


def _canonical_episode(episode: Episode) -> dict[str, Any]:
    return {field: episode.get(field) for field in CANONICAL_FIELDS}


def episode_fingerprint(episode: Episode) -> str:
    payload = json.dumps(
        _canonical_episode(episode),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def content_chars(episodes: Sequence[Episode]) -> int:
    """Stable information-volume proxy used only to validate matched controls."""

    total = 0
    for episode in episodes:
        for field, value in _canonical_episode(episode).items():
            if field in {"episode_id", "chat_id", "timestamp"}:
                continue
            if isinstance(value, list):
                total += sum(len(str(item)) for item in value)
            elif value is not None:
                total += len(str(value))
    return total


def adjacency_signature(episodes: Sequence[Episode]) -> str:
    pairs = [
        f"{_episode_id(left)}->{_episode_id(right)}"
        for left, right in zip(episodes, episodes[1:])
    ]
    return hashlib.sha256("|".join(pairs).encode("utf-8")).hexdigest()


def history_shuffled(episodes: Sequence[Episode]) -> list[dict[str, Any]]:
    """Change interior lineage while preserving the same episodes and endpoints."""

    copied = [dict(episode) for episode in episodes]
    if len(copied) < 4:
        raise ValueError("at least four episodes are required for lineage ablation")

    interior = copied[1:-1]
    rotated = interior[1:] + interior[:1]
    if rotated == interior:
        rotated = list(reversed(interior))
    return [copied[0], *rotated, copied[-1]]


def endpoint_matched_lineage(episodes: Sequence[Episode]) -> list[dict[str, Any]]:
    """Preserve start/end and content volume but reverse the interior path."""

    copied = [dict(episode) for episode in episodes]
    if len(copied) < 4:
        raise ValueError("at least four episodes are required for lineage ablation")
    return [copied[0], *reversed(copied[1:-1]), copied[-1]]


def _validate_unique_ids(episodes: Sequence[Episode]) -> None:
    ids = [_episode_id(episode) for episode in episodes]
    if len(ids) != len(set(ids)):
        raise ValueError("episode_id values must be unique")


def _validate_matched_control(
    intact: Sequence[Episode],
    control: Sequence[Episode],
) -> None:
    intact_fingerprints = sorted(episode_fingerprint(episode) for episode in intact)
    control_fingerprints = sorted(episode_fingerprint(episode) for episode in control)

    if intact_fingerprints != control_fingerprints:
        raise ValueError("control must preserve the exact episode multiset")
    if _episode_id(intact[0]) != _episode_id(control[0]):
        raise ValueError("control must preserve the starting endpoint")
    if _episode_id(intact[-1]) != _episode_id(control[-1]):
        raise ValueError("control must preserve the terminal endpoint")
    if content_chars(intact) != content_chars(control):
        raise ValueError("control must preserve information volume")
    if adjacency_signature(intact) == adjacency_signature(control):
        raise ValueError("control must materially change lineage adjacency")


def build_control_pack(episodes: Sequence[Episode]) -> dict[str, Any]:
    """Build three frozen conditions for blinded downstream evaluation."""

    intact = [dict(episode) for episode in episodes]
    if len(intact) < 4:
        raise ValueError("at least four episodes are required")
    _validate_unique_ids(intact)

    shuffled = history_shuffled(intact)
    endpoint_matched = endpoint_matched_lineage(intact)
    _validate_matched_control(intact, shuffled)
    _validate_matched_control(intact, endpoint_matched)

    return {
        "version": "0.1",
        "status": "CONTROL_PACK_READY",
        "episode_count": len(intact),
        "content_chars": content_chars(intact),
        "start_episode_id": _episode_id(intact[0]),
        "terminal_episode_id": _episode_id(intact[-1]),
        "conditions": {
            "intact": {
                "adjacency_sha256": adjacency_signature(intact),
                "episodes": intact,
            },
            "shuffled": {
                "adjacency_sha256": adjacency_signature(shuffled),
                "episodes": shuffled,
            },
            "endpoint_matched": {
                "adjacency_sha256": adjacency_signature(endpoint_matched),
                "episodes": endpoint_matched,
            },
        },
        "claim_boundary": (
            "A control pack validates matched lineage interventions only. "
            "It is not evidence for relational intelligence until blinded "
            "downstream task scores show a lineage-specific functional gain."
        ),
    }


def score_judgments(judgments: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Score blinded downstream task judgments across matched conditions.

    Input rows require: condition, task_id, score. Score must be in [0,1].
    Every condition must contain the same task IDs.
    """

    grouped: dict[str, dict[str, float]] = defaultdict(dict)
    for row in judgments:
        condition = str(row["condition"])
        task_id = str(row["task_id"])
        score = float(row["score"])
        if not 0.0 <= score <= 1.0:
            raise ValueError("judgment scores must be in [0,1]")
        if task_id in grouped[condition]:
            raise ValueError(f"duplicate task_id {task_id!r} in {condition!r}")
        grouped[condition][task_id] = score

    required = {"intact", "shuffled", "endpoint_matched"}
    if not required.issubset(grouped):
        missing = sorted(required - set(grouped))
        raise ValueError(f"missing conditions: {missing}")

    task_sets = [set(grouped[name]) for name in sorted(required)]
    if not task_sets[0] or any(tasks != task_sets[0] for tasks in task_sets[1:]):
        raise ValueError("all conditions must contain the same non-empty task set")

    means = {
        condition: mean(grouped[condition].values())
        for condition in sorted(required)
    }
    result = LineageScore(
        intact=means["intact"],
        shuffled=means["shuffled"],
        endpoint_matched=means["endpoint_matched"],
    )

    return {
        "status": "SCORED",
        "task_count": len(task_sets[0]),
        "condition_means": means,
        "history_gain": result.history_gain,
        "lineage_specificity": result.lineage_specificity,
        "candidate_signature": result.candidate_signature(),
        "claim_boundary": (
            "A positive signature is evidence only that the scored function "
            "depends on the preserved tested lineage under these controls."
        ),
    }


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: str, value: Any) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="build matched lineage controls")
    build.add_argument("episodes", help="JSON list of frozen MELLOMROM episodes")
    build.add_argument("output", help="output control-pack JSON")

    score = subparsers.add_parser("score", help="score blinded task judgments")
    score.add_argument("judgments", help="JSON list of condition/task/score rows")
    score.add_argument("output", help="output score JSON")

    args = parser.parse_args()
    if args.command == "build":
        episodes = _load_json(args.episodes)
        if not isinstance(episodes, list):
            raise ValueError("episodes input must be a JSON list")
        _write_json(args.output, build_control_pack(episodes))
    else:
        judgments = _load_json(args.judgments)
        if not isinstance(judgments, list):
            raise ValueError("judgments input must be a JSON list")
        _write_json(args.output, score_judgments(judgments))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
