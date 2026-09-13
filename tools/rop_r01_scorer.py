"""ROP-R01 Blind Scorer Process.

Strictly adheres to pre-registration blinding constraints:
1. Has NO access to assignment manifest or condition labels (fails closed if present).
2. Fails closed if condition scaffolding or raw prompt/response leaks into blinded input.
3. Scores mathematical correctness objectively against the frozen answer key.
4. Scores dependency preservation objectively against the frozen dependency map (not derived from correctness).
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional
import uuid


class ScorerBlindingError(RuntimeError):
    """Raised when a condition label, prompt, or structural leakage reaches the scorer."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def assert_no_manifest_or_conditions(path: Path) -> None:
    path_str = str(path).lower()
    if "manifest" in path_str or "assignment" in path_str:
        raise ScorerBlindingError(
            f"BLINDING VIOLATION: Scorer process must never receive assignment manifest: {path}"
        )


def score_responses(
    blinded_responses_path: Path,
    answer_key_path: Path,
    dependency_map_path: Path,
    output_scores_path: Path,
    scorer_id: Optional[str] = None,
    tolerance: float = 1e-6,
) -> None:
    assert_no_manifest_or_conditions(blinded_responses_path)
    assert_no_manifest_or_conditions(answer_key_path)
    assert_no_manifest_or_conditions(dependency_map_path)
    assert_no_manifest_or_conditions(output_scores_path)

    scorer_id = scorer_id or f"scorer-{uuid.uuid4().hex[:12]}"

    # Load answer key
    answer_key: Dict[str, float] = {}
    with answer_key_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                answer_key[item["task_id"]] = float(item["answer"])

    # Load dependency map
    with dependency_map_path.open("r", encoding="utf-8") as f:
        dep_data = json.load(f)
    task_pairs_dep = dep_data.get("task_pairs", {})

    forbidden_tokens = (
        "condition",
        "C0",
        "C2",
        "C3",
        "raw_response",
        "prompt",
        "DECOMPOSITION",
        "REDUCTIONS",
        "RESIDUAL",
        "MECHANISM",
    )

    scored_records: List[Dict[str, Any]] = []
    correct_count = 0
    dep_preserved_count = 0
    total_count = 0

    print(f"[{scorer_id}] Scoring blinded responses from {blinded_responses_path}...")

    with blinded_responses_path.open("r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            if not line.strip():
                continue
            record = json.loads(line)

            # Strict blinding check: no condition fields, prompt, raw_response, or structural tokens
            for token in forbidden_tokens:
                if re.search(rf"\b{re.escape(token)}\b", line, flags=re.IGNORECASE):
                    raise ScorerBlindingError(
                        f"BLINDING VIOLATION on line {line_num}: token '{token}' detected in blinded input"
                    )

            task_id = record["task_id"]
            pair_id = record.get("pair_id")

            if task_id not in answer_key:
                raise ValueError(f"Task ID {task_id} not found in answer key!")

            expected = answer_key[task_id]
            submitted = record.get("submitted_answer")

            # 1. Correctness scoring (independent of dependency preservation)
            if submitted is not None and not math.isnan(submitted):
                is_correct = 1 if abs(float(submitted) - expected) <= tolerance else 0
            else:
                is_correct = 0

            # 2. Objective dependency preservation scoring against frozen dependency map
            # Independent of whether the final answer is correct or not!
            intermediate_vals: List[float] = [float(v) for v in record.get("intermediate_values", [])]
            required_vals: List[float] = []
            if pair_id and pair_id in task_pairs_dep:
                required_vals = [float(v) for v in task_pairs_dep[pair_id].get("required_intermediate_values", [])]

            if not required_vals:
                # If no intermediate values are required, dependency preservation defaults to 1
                dep_preserved = 1
            else:
                # All required intermediate values must be reflected in the intermediate calculations
                all_found = True
                for req in required_vals:
                    if not any(abs(req - iv) <= tolerance for iv in intermediate_vals):
                        all_found = False
                        break
                dep_preserved = 1 if all_found else 0

            if is_correct:
                correct_count += 1
            if dep_preserved:
                dep_preserved_count += 1
            total_count += 1

            scored_item = {
                "task_id": task_id,
                "pair_id": pair_id,
                "submitted_answer": submitted,
                "expected_answer": expected,
                "correct": is_correct,
                "required_dependency_preserved": dep_preserved,
                "time_seconds": record.get("time_seconds"),
                "steps": record.get("steps"),
                "reversals": record.get("reversals"),
                "errors": record.get("errors"),
                "confidence": record.get("confidence"),
                "executor_session_id": record.get("executor_session_id"),
                "scorer_id": scorer_id,
                "scored_at": _now_iso(),
            }
            scored_records.append(scored_item)

    output_scores_path.parent.mkdir(parents=True, exist_ok=True)
    with output_scores_path.open("w", encoding="utf-8") as f:
        for item in scored_records:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    accuracy = (correct_count / total_count * 100.0) if total_count > 0 else 0.0
    dep_rate = (dep_preserved_count / total_count * 100.0) if total_count > 0 else 0.0
    print(
        f"[{scorer_id}] Blind scoring complete. Scored {total_count} tasks. "
        f"Accuracy: {accuracy:.1f}% ({correct_count}/{total_count}) | "
        f"Dep preservation: {dep_rate:.1f}% ({dep_preserved_count}/{total_count}). "
        f"Output: {output_scores_path}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="ROP-R01 Blind Scorer Process")
    parser.add_argument("--blinded-responses", type=Path, default=Path("runs/ROP-R01/blinded-responses-v0.1.jsonl"))
    parser.add_argument("--answer-key", type=Path, default=Path("runs/ROP-R01/answer-key-v0.1.jsonl"))
    parser.add_argument("--dependency-map", type=Path, default=Path("runs/ROP-R01/dependency-map-v0.1.json"))
    parser.add_argument("--output-scores", type=Path, default=Path("runs/ROP-R01/blinded-scores-v0.1.jsonl"))
    parser.add_argument("--scorer-id", type=str, default=None)
    parser.add_argument("--tolerance", type=float, default=1e-6)
    args = parser.parse_args()

    score_responses(
        blinded_responses_path=args.blinded_responses,
        answer_key_path=args.answer_key,
        dependency_map_path=args.dependency_map,
        output_scores_path=args.output_scores,
        scorer_id=args.scorer_id,
        tolerance=args.tolerance,
    )


if __name__ == "__main__":
    main()
