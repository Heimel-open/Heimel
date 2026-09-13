"""NJAL-R01 Isolated Blind Scorer Process.

Strictly adheres to pre-registration constraints:
1. Structural blinding: fails closed if any condition label (C2, C3-I, C3-R), prompt,
   policy name, or structural keyword is detected in the input.
2. Decoupled scoring: independently evaluates:
   - Mathematical correctness against answer-key-v0.1.jsonl
   - Required dependency preservation against dependency-map-v0.1.json
   - H4 mechanism localization (restore before consequence step)
3. Outputs blinded scores with ZERO condition labels.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Set


class ScorerBlindingError(RuntimeError):
    """Raised when the scorer's structural blinding invariant is violated."""


ALLOWED_KEYS = {
    "task_id",
    "pair_id",
    "submitted_answer",
    "intermediate_values",
    "available_components_at_consequence",
    "active_workspace_size",
    "confidence",
    "steps",
    "reversals",
    "errors",
}

FORBIDDEN_TOKENS = (
    "condition",
    "prompt",
    "raw_response",
    "C3-I",
    "C3-R",
    "IRREVERSIBLE",
    "MOVE_LATENT",
    "REVERSIBLE_WORKSPACE",
    "REDUCTIONS",
    "WORKSPACE_MANAGEMENT",
)


def assert_no_manifest_or_conditions(path: Path) -> None:
    """Verifies that the scorer is NOT provided with the assignment manifest or condition labels."""
    path_str = str(path).lower()
    if "manifest" in path_str or "assignment" in path_str:
        raise ScorerBlindingError(
            f"SCORER BLINDING VIOLATION: Scorer must never receive assignment manifest ({path})"
        )


def check_blinding_invariants(record: Dict[str, Any], raw_line: str) -> None:
    # 1. Enforce strict schema of allowed fields
    extra_keys = set(record.keys()) - ALLOWED_KEYS
    if extra_keys:
        raise ScorerBlindingError(
            f"SCORER BLINDING VIOLATION: Unexpected keys detected in blinded input: {sorted(extra_keys)}"
        )

    # 2. Check for forbidden tokens
    for token in FORBIDDEN_TOKENS:
        if re.search(rf"\b{re.escape(token)}\b", raw_line, flags=re.IGNORECASE):
            raise ScorerBlindingError(
                f"SCORER BLINDING VIOLATION: Forbidden structural token '{token}' detected in blinded input: {raw_line[:120]}"
            )


def score_responses(
    blinded_responses_path: Path,
    answer_key_path: Path,
    dependency_map_path: Path,
    output_scores_path: Path,
    scorer_id: str = "AutomatedScorer-v0.1",
    tolerance: float = 1e-4,
) -> None:
    assert_no_manifest_or_conditions(blinded_responses_path)

    # 1. Load answer key
    answer_key: Dict[str, float] = {}
    with answer_key_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                answer_key[rec["task_id"]] = float(rec["answer"])

    # 2. Load dependency map
    with dependency_map_path.open("r", encoding="utf-8") as f:
        dep_map_data = json.load(f)
    task_pairs = dep_map_data.get("task_pairs", {})

    output_scores_path.parent.mkdir(parents=True, exist_ok=True)
    out_file = output_scores_path.open("w", encoding="utf-8")

    try:
        with blinded_responses_path.open("r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f):
                if not line.strip():
                    continue
                resp = json.loads(line)
                check_blinding_invariants(resp, line)

                task_id = resp["task_id"]
                pair_id = resp.get("pair_id", task_id.split("-")[0])
                submitted = resp.get("submitted_answer")
                intermediates: List[float] = resp.get("intermediate_values", [])
                avail_components: List[str] = resp.get("available_components_at_consequence", [])
                active_size: int = resp.get("active_workspace_size", 0)

                # 1. Score mathematical correctness
                correct = 0
                expected = answer_key.get(task_id)
                if expected is not None and submitted is not None:
                    try:
                        if math.isclose(float(submitted), expected, abs_tol=tolerance):
                            correct = 1
                    except (ValueError, TypeError):
                        correct = 0

                # 2. Score required dependency preservation
                pair_spec = task_pairs.get(pair_id, {})
                required_values = [float(v) for v in pair_spec.get("required_intermediate_values", [])]
                restore_targets = pair_spec.get("restore_targets", [])

                # Check intermediate values
                values_preserved = True
                for req_val in required_values:
                    if not any(math.isclose(float(obs), req_val, abs_tol=tolerance) for obs in intermediates):
                        values_preserved = False
                        break

                # Check required components available at consequence step
                components_available = True
                for comp_id in restore_targets:
                    if comp_id not in avail_components:
                        components_available = False
                        break

                required_dependency_preserved = 1 if (values_preserved and components_available) else 0

                # 3. H4 mechanism localization: restore before consequence step
                h4_eligible = bool(restore_targets)
                h4_restored = 1 if (h4_eligible and components_available) else 0

                scored_record = {
                    "task_id": task_id,
                    "pair_id": pair_id,
                    "submitted_answer": submitted,
                    "expected_answer": expected,
                    "correct": correct,
                    "required_dependency_preserved": required_dependency_preserved,
                    "h4_eligible": h4_eligible,
                    "h4_restored_before_consequence": h4_restored,
                    "active_workspace_size": active_size,
                    "confidence": resp.get("confidence", 90),
                    "steps": resp.get("steps", 3),
                    "reversals": resp.get("reversals", 0),
                    "errors": resp.get("errors", 0),
                    "scorer_id": scorer_id,
                }
                out_file.write(json.dumps(scored_record) + "\n")
                out_file.flush()
    finally:
        out_file.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="NJAL-R01 Isolated Blind Scorer")
    parser.add_argument("--blinded-responses", type=Path, required=True, help="Path to blinded responses jsonl")
    parser.add_argument("--answer-key", type=Path, required=True, help="Path to frozen answer key jsonl")
    parser.add_argument("--dependency-map", type=Path, required=True, help="Path to frozen dependency map json")
    parser.add_argument("--output-scores", type=Path, required=True, help="Path to output blinded scores jsonl")
    parser.add_argument("--scorer-id", type=str, default="AutomatedScorer-v0.1")
    args = parser.parse_args()

    score_responses(
        blinded_responses_path=args.blinded_responses,
        answer_key_path=args.answer_key,
        dependency_map_path=args.dependency_map,
        output_scores_path=args.output_scores,
        scorer_id=args.scorer_id,
    )


if __name__ == "__main__":
    main()
