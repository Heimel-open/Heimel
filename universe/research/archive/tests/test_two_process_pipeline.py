"""Tests for the ROP-R01 Two-Process Isolated Pipeline.

Corroborates all three blinding and isolation fixes:
1. Physical isolation: Executor cannot access the answer key in its environment.
2. Structural blinding: Scorer input is strictly stripped of prompts, raw_response,
   and structural condition tokens (REDUCTIONS, RESIDUAL, MECHANISM, DECOMPOSITION).
3. Independent dependency scoring: Correctness and required dependency preservation
   are decoupled and independently scored against the frozen dependency map.
4. End-to-end dry run: Full 48-task execution with sandbox isolation and hypothesis analysis.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
import subprocess
import sys
import tempfile

from tools.rop_r01_executor import ExecutorIsolationError, assert_physical_isolation
from tools.rop_r01_scorer import ScorerBlindingError, assert_no_manifest_or_conditions, score_responses
from tools.rop_r01_pipeline import run_pipeline


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "runs" / "ROP-R01" / "assignment-manifest-v0.1.json"
TASKS_PATH = REPO_ROOT / "runs" / "ROP-R01" / "task-set-v0.1.jsonl"
ANSWER_KEY_PATH = REPO_ROOT / "runs" / "ROP-R01" / "answer-key-v0.1.jsonl"
DEPENDENCY_MAP_PATH = REPO_ROOT / "runs" / "ROP-R01" / "dependency-map-v0.1.json"


def test_executor_fails_closed_if_answer_key_passed_in_args():
    with pytest.raises(ExecutorIsolationError, match="Path references answer key"):
        assert_physical_isolation(ANSWER_KEY_PATH, TASKS_PATH)


def test_executor_fails_closed_if_answer_key_in_working_tree(tmp_path, monkeypatch):
    # Simulate answer-key file existing in cwd
    fake_key = tmp_path / "answer-key-v0.1.jsonl"
    fake_key.write_text('{"task_id": "E01-A", "answer": 31}\n')
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


def test_scorer_fails_closed_if_structural_tokens_leak_into_responses(tmp_path):
    # Leak C3 structural keywords into blinded input
    leaked_file = tmp_path / "leaked_responses.jsonl"
    fake_record = {
        "task_id": "E01-A",
        "submitted_answer": 31,
        "note": "REDUCTIONS: C1: RESOLVED -> KEEP",  # STRUCTURAL LEAK!
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
    """Corroborates that dependency preservation is NOT tautologically equal to correctness.

    Task E01 requires intermediate product 48.
    Case A: Correct answer 31, but intermediate 48 is missing -> correct=1, dep_preserved=0.
    Case B: Wrong answer 30, but intermediate 48 is preserved -> correct=0, dep_preserved=1.
    """
    responses_file = tmp_path / "test_responses.jsonl"
    records = [
        # Case A: Correct answer (31), missing required intermediate value (48)
        {
            "task_id": "E01-A",
            "pair_id": "E01",
            "submitted_answer": 31.0,
            "intermediate_values": [17.0],  # 48 is missing!
        },
        # Case B: Incorrect answer (30), but required intermediate value (48) is present
        {
            "task_id": "E01-B",
            "pair_id": "E01",
            "submitted_answer": 30.0,       # Wrong answer!
            "intermediate_values": [48.0, 17.0],  # 48 is preserved!
        },
    ]
    responses_file.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    out_scores = tmp_path / "scores.jsonl"

    score_responses(
        blinded_responses_path=responses_file,
        answer_key_path=ANSWER_KEY_PATH,
        dependency_map_path=DEPENDENCY_MAP_PATH,
        output_scores_path=out_scores,
    )

    scores = [json.loads(line) for line in out_scores.read_text().splitlines()]
    assert len(scores) == 2

    # Case A: Correct final answer, but severed dependency
    assert scores[0]["correct"] == 1
    assert scores[0]["required_dependency_preserved"] == 0

    # Case B: Incorrect final answer, but preserved required dependency
    assert scores[1]["correct"] == 0
    assert scores[1]["required_dependency_preserved"] == 1


def test_end_to_end_dry_run_pipeline_execution(tmp_path):
    output_dir = tmp_path / "run_output"

    run_pipeline(
        manifest_path=MANIFEST_PATH,
        tasks_path=TASKS_PATH,
        answer_key_path=ANSWER_KEY_PATH,
        dependency_map_path=DEPENDENCY_MAP_PATH,
        output_dir=output_dir,
        backend="mock",
        dry_run=True,
    )

    events_path = output_dir / "audit-events-v0.1.jsonl"
    blinded_resp_path = output_dir / "blinded-responses-v0.1.jsonl"
    blinded_scores_path = output_dir / "blinded-scores-v0.1.jsonl"
    report_path = output_dir / "analysis-report-v0.1.json"
    summary_path = output_dir / "analysis-summary-v0.1.md"

    assert events_path.exists()
    assert blinded_resp_path.exists()
    assert blinded_scores_path.exists()
    assert report_path.exists()
    assert summary_path.exists()

    # Verify blinded responses contain exactly 48 tasks and ZERO condition labels, prompts, or structural tokens
    blinded_lines = blinded_resp_path.read_text().splitlines()
    assert len(blinded_lines) == 48
    for line in blinded_lines:
        record = json.loads(line)
        assert "condition" not in record
        assert "prompt" not in record
        assert "raw_response" not in record
        line_str = line
        for token in ("C0", "C2", "C3", "REDUCTIONS", "RESIDUAL", "MECHANISM", "DECOMPOSITION"):
            assert f'"{token}"' not in line_str

    # Verify blinded scores contain 48 tasks
    score_lines = blinded_scores_path.read_text().splitlines()
    assert len(score_lines) == 48

    # Verify report structure
    report = json.loads(report_path.read_text())
    assert report["total_tasks"] == 48
    assert "C0" in report["conditions"]
    assert "C2" in report["conditions"]
    assert "C3" in report["conditions"]
    assert "H1" in report["hypotheses"]
    assert "H2" in report["hypotheses"]
    assert "kill_rules" in report
