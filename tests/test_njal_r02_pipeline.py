"""Tests for the NJAL-R02 Governed Reactivation Two-Process Isolated Pipeline.

Corroborates all pre-registration blinding and isolation gates:
1. Physical isolation: Executor cannot access the answer key in arguments or filesystem.
2. Condition-neutral blinding: Scorer strictly fails closed if manifest, condition labels
   (C2, C3-R-M, C3-R-G), or structural tokens leak into blinded responses.
3. Decoupled scoring: Correctness and required dependency preservation are independently scored.
4. Core method invariants:
   - CLASSIFICATION_IS_NOT_DELETION_AUTHORITY
   - LATENT_AVAILABILITY_IS_NOT_RESTORE_AUTHORITY
   - EXECUTION_HARNESS_HOLDS_CONSEQUENCE_AUTHORITY
5. End-to-end dry run: Full 72-task execution with sandbox isolation, blind scoring, and hypothesis analysis.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
import subprocess
import sys
import tempfile

from tools.njal_r02_executor import ExecutorIsolationError, assert_physical_isolation
from tools.njal_r02_scorer import ScorerBlindingError, assert_no_manifest_or_conditions, score_responses
from tools.njal_r02_pipeline import run_pipeline


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "runs" / "NJAL-R02" / "assignment-manifest-v0.1.json"
TASKS_PATH = REPO_ROOT / "runs" / "NJAL-R02" / "task-set-v0.1.jsonl"
ANSWER_KEY_PATH = REPO_ROOT / "runs" / "NJAL-R02" / "answer-key-v0.1.jsonl"
DEPENDENCY_MAP_PATH = REPO_ROOT / "runs" / "NJAL-R02" / "dependency-map-v0.1.json"


def test_executor_fails_closed_if_answer_key_passed_in_args():
    with pytest.raises(ExecutorIsolationError, match="Path references answer key"):
        assert_physical_isolation(ANSWER_KEY_PATH, TASKS_PATH)


def test_executor_fails_closed_if_answer_key_in_working_tree(tmp_path, monkeypatch):
    fake_key = tmp_path / "answer-key-v0.1.jsonl"
    fake_key.write_text('{"task_id": "L01-A", "answer": 65}\n')
    fake_manifest = tmp_path / "manifest.json"
    fake_manifest.write_text("{}")
    fake_tasks = tmp_path / "tasks.jsonl"
    fake_tasks.write_text("{}")

    monkeypatch.chdir(tmp_path)
    with pytest.raises(ExecutorIsolationError, match="Answer key file found in executor cwd"):
        assert_physical_isolation(fake_manifest, fake_tasks)


def test_scorer_fails_closed_if_manifest_passed():
    with pytest.raises(ScorerBlindingError, match="must never receive assignment manifest"):
        assert_no_manifest_or_conditions(MANIFEST_PATH)


def test_scorer_fails_closed_if_condition_or_structural_tokens_leak(tmp_path):
    leaked_file = tmp_path / "leaked_responses.jsonl"
    fake_record = {
        "task_id": "L01-A",
        "submitted_answer": 65,
        "note": "condition: C3-R-G",  # LEAK!
    }
    leaked_file.write_text(json.dumps(fake_record) + "\n")
    out_scores = tmp_path / "scores.jsonl"

    with pytest.raises(ScorerBlindingError, match="detected in blinded input"):
        score_responses(
            blinded_responses_path=leaked_file,
            answer_key_path=ANSWER_KEY_PATH,
            dependency_map_path=DEPENDENCY_MAP_PATH,
            output_scores_path=out_scores,
        )


def test_dependency_preservation_is_decoupled_from_correctness(tmp_path):
    responses_file = tmp_path / "test_responses.jsonl"
    records = [
        # Case A: Correct final answer (65), but missing required intermediate 84
        {
            "task_id": "L01-A",
            "pair_id": "L01",
            "submitted_answer": 65.0,
            "intermediate_values": [19.0],  # 84 is missing
            "available_components_at_consequence": ["C1", "C2"],
        },
        # Case B: Incorrect final answer (50), but required intermediate 84 is present
        {
            "task_id": "L01-B",
            "pair_id": "L01",
            "submitted_answer": 50.0,       # Wrong answer
            "intermediate_values": [84.0, 19.0],  # 84 is preserved
            "available_components_at_consequence": ["C1", "C2"],
        },
    ]
    with responses_file.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    scores_file = tmp_path / "test_scores.jsonl"
    score_responses(
        blinded_responses_path=responses_file,
        answer_key_path=ANSWER_KEY_PATH,
        dependency_map_path=DEPENDENCY_MAP_PATH,
        output_scores_path=scores_file,
    )

    scored = []
    with scores_file.open("r", encoding="utf-8") as f:
        for line in f:
            scored.append(json.loads(line))

    assert len(scored) == 2
    # Case A: correct=1, dep=0
    assert scored[0]["correct"] == 1
    assert scored[0]["required_dependency_preserved"] == 0

    # Case B: correct=0, dep=1
    assert scored[1]["correct"] == 0
    assert scored[1]["required_dependency_preserved"] == 1


def test_invariants_governed_state_machine(tmp_path):
    """Corroborates that C3-R-G harness deterministically activates required latent state."""
    # Under C3-R-G, task D01 has restore_target C1.
    # Harness state machine must trigger activation for C1 and keep C2 latent.
    from tools.njal_r02_executor import mock_solver
    with open(DEPENDENCY_MAP_PATH, "r", encoding="utf-8") as f:
        dep_map = json.load(f)

    task = {"task_id": "D01-A", "pair_id": "D01"}
    dep_spec = dep_map["task_pairs"]["D01"]

    res_g = mock_solver(task, "C3-R-G", dep_spec)
    assert "C1" in res_g["available_components_at_consequence"]
    assert "C2" not in res_g["available_components_at_consequence"]
    assert any(ev["event_type"] == "GOVERNED_CONSEQUENCE_TRIGGERED" for ev in res_g["events"])
    assert res_g["active_size"] < 5  # Reduced workspace preserved


def test_end_to_end_dry_run_72_task_execution(tmp_path):
    """Executes the complete 72-task pipeline end-to-end under mock backend."""
    output_dir = tmp_path / "njal_r02_run"

    run_pipeline(
        manifest_path=MANIFEST_PATH,
        tasks_path=TASKS_PATH,
        answer_key_path=ANSWER_KEY_PATH,
        dependency_map_path=DEPENDENCY_MAP_PATH,
        output_dir=output_dir,
        backend="mock",
        dry_run=True,
    )

    # 1. Check audit log
    audit_path = output_dir / "audit-events-v0.1.jsonl"
    assert audit_path.exists()
    events = [json.loads(line) for line in audit_path.read_text().splitlines() if line.strip()]
    assert len(events) >= 72
    assert events[0]["event_type"] == "PROTOCOL_SEALED"
    assert any(ev["event_type"] == "GOVERNED_CONSEQUENCE_TRIGGERED" for ev in events)

    # 2. Check blinded responses
    blinded_resp_path = output_dir / "blinded-responses-v0.1.jsonl"
    assert blinded_resp_path.exists()
    responses = [json.loads(line) for line in blinded_resp_path.read_text().splitlines() if line.strip()]
    assert len(responses) == 72
    # Ensure zero condition tokens leak
    for line in blinded_resp_path.read_text().splitlines():
        for token in ("C3-R-M", "C3-R-G", "condition", "prompt", "GOVERNED"):
            assert token not in line

    # 3. Check blinded scores
    blinded_scores_path = output_dir / "blinded-scores-v0.1.jsonl"
    assert blinded_scores_path.exists()
    scores = [json.loads(line) for line in blinded_scores_path.read_text().splitlines() if line.strip()]
    assert len(scores) == 72
    for s in scores:
        assert "condition" not in s

    # 4. Check analysis report
    report_path = output_dir / "analysis-report-v0.1.json"
    assert report_path.exists()
    with report_path.open("r", encoding="utf-8") as f:
        report = json.load(f)

    assert report["total_tasks"] == 72
    assert "C2" in report["conditions"]
    assert "C3-R-M" in report["conditions"]
    assert "C3-R-G" in report["conditions"]

    # In mock run, C3-R-G should pass all hypotheses H1-H4
    assert report["hypotheses"]["H1"]["passed"] is True
    assert report["hypotheses"]["H2"]["passed"] is True
    assert report["hypotheses"]["H3"]["passed"] is True
    assert report["hypotheses"]["H4"]["passed"] is True
    assert report["all_kill_rules_passed"] is True
    assert report["final_decision"] == "CONFIRMED"
