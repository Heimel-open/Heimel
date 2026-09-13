"""Tests for the NJAL-R01 Reversible Workspace Two-Process Isolated Pipeline.

Corroborates all pre-registration blinding and isolation gates:
1. Physical isolation: Executor cannot access the answer key in arguments or filesystem.
2. Condition-neutral blinding: Scorer strictly fails closed if manifest, condition labels
   (C2, C3-I, C3-R), or structural tokens leak into blinded responses.
3. Decoupled scoring: Correctness and required dependency preservation are independently scored.
4. Core method invariant: CLASSIFICATION_IS_NOT_DELETION_AUTHORITY — C3-R moves to latent, does not delete.
5. End-to-end dry run: Full 72-task execution with sandbox isolation, blind scoring, and hypothesis analysis.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
import subprocess
import sys
import tempfile

from tools.njal_r01_executor import ExecutorIsolationError, assert_physical_isolation
from tools.njal_r01_scorer import ScorerBlindingError, assert_no_manifest_or_conditions, score_responses
from tools.njal_r01_pipeline import run_pipeline


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "runs" / "NJAL-R01" / "assignment-manifest-v0.1.json"
TASKS_PATH = REPO_ROOT / "runs" / "NJAL-R01" / "task-set-v0.1.jsonl"
ANSWER_KEY_PATH = REPO_ROOT / "runs" / "NJAL-R01" / "answer-key-v0.1.jsonl"
DEPENDENCY_MAP_PATH = REPO_ROOT / "runs" / "NJAL-R01" / "dependency-map-v0.1.json"


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
        "note": "condition: C3-R",  # LEAK!
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
    """Verifies that mathematical correctness and dependency preservation are decoupled.

    Task L01 requires intermediate product 84 and answer 65.
    Case A: Correct answer 65, but intermediate 84 is missing -> correct=1, dep_preserved=0.
    Case B: Wrong answer 50, but intermediate 84 is present -> correct=0, dep_preserved=1.
    """
    responses_file = tmp_path / "test_responses.jsonl"
    records = [
        # Case A: Correct final answer (65), but missing required intermediate 84
        {
            "task_id": "L01-A",
            "pair_id": "L01",
            "submitted_answer": 65.0,
            "intermediate_values": [19.0],  # 84 is missing!
            "available_components_at_consequence": ["C1", "C2"],
        },
        # Case B: Incorrect final answer (50), but required intermediate 84 is present
        {
            "task_id": "L01-B",
            "pair_id": "L01",
            "submitted_answer": 50.0,       # Wrong answer!
            "intermediate_values": [84.0, 19.0],  # 84 is preserved!
            "available_components_at_consequence": ["C1", "C2"],
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

    # Case A: Correct answer, severed dependency
    assert scores[0]["correct"] == 1
    assert scores[0]["required_dependency_preserved"] == 0

    # Case B: Incorrect answer, preserved dependency
    assert scores[1]["correct"] == 0
    assert scores[1]["required_dependency_preserved"] == 1


def test_invariant_classification_is_not_deletion_authority(tmp_path):
    """Corroborates that C3-R moves components to latent state and can restore them,

    while C3-I irreversibly removes components and cannot restore them.
    Invariants:
    - CLASSIFICATION_IS_NOT_DELETION_AUTHORITY
    - ABSENCE_FROM_ACTIVE_WORKSPACE_DOES_NOT_IMPLY_ABSENCE_FROM_SYSTEM_STATE
    """
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
    events = [json.loads(line) for line in events_path.read_text().splitlines()]

    # Check that C3-R tasks emitted COMPONENT_MOVED_LATENT, RESTORE_REQUESTED, COMPONENT_RESTORED
    c3r_latent_events = [e for e in events if e.get("event_type") == "COMPONENT_MOVED_LATENT"]
    c3r_restore_events = [e for e in events if e.get("event_type") == "COMPONENT_RESTORED"]
    assert len(c3r_latent_events) > 0
    assert len(c3r_restore_events) > 0

    # Check that C3-I emitted COMPONENT_REMOVED_IRREVERSIBLE
    c3i_removed_events = [e for e in events if e.get("event_type") == "COMPONENT_REMOVED_IRREVERSIBLE"]
    assert len(c3i_removed_events) > 0


def test_end_to_end_dry_run_72_task_execution(tmp_path):
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

    # Verify blinded responses contain exactly 72 tasks and ZERO condition tokens
    blinded_lines = blinded_resp_path.read_text().splitlines()
    assert len(blinded_lines) == 72
    for line in blinded_lines:
        record = json.loads(line)
        assert "condition" not in record
        assert "prompt" not in record
        assert "raw_response" not in record
        assert record.get("condition") is None
        line_str = line
        for token in ("C3-I", "C3-R", "IRREVERSIBLE", "MOVE_LATENT", "WORKSPACE_MANAGEMENT", "REDUCTIONS"):
            assert f'"{token}"' not in line_str

    # Verify blinded scores contain 72 tasks
    score_lines = blinded_scores_path.read_text().splitlines()
    assert len(score_lines) == 72

    # Verify report structure & frozen hypotheses
    report = json.loads(report_path.read_text())
    assert report["total_tasks"] == 72
    assert "C2" in report["conditions"]
    assert "C3-I" in report["conditions"]
    assert "C3-R" in report["conditions"]
    assert "H1" in report["hypotheses"]
    assert "H2" in report["hypotheses"]
    assert "H3" in report["hypotheses"]
    assert "H4" in report["hypotheses"]
    assert report["all_kill_rules_passed"] is True
    assert report["final_decision"] == "CONFIRMED"
