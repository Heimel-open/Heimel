from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


RUNNER_PATH = Path("apps/governed-media-office/close_shadow_day.py")


def _load_runner():
    spec = importlib.util.spec_from_file_location("governed_media_close_shadow_day", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _start_measurement() -> dict:
    return {
        "schema_version": "governed-media-founder-measurement/v1",
        "cycle_id": "linkedin-shadow-2026-07-28",
        "day": 1,
        "record_date": "2026-07-28",
        "channel": "linkedin",
        "status": "open",
        "baseline": {
            "minimum_manual_minutes": 120,
            "maximum_manual_minutes": 180,
            "basis": "Founder self-report.",
        },
        "observed": {
            "review_minutes": None,
            "relationship_minutes": None,
        },
        "time_saving": {
            "automated_production_minutes_avoided": None,
            "automation_rate": None,
        },
        "publication_enabled": False,
    }


def test_close_runner_builds_observed_founder_time_record(tmp_path: Path) -> None:
    runner = _load_runner()
    start_path = tmp_path / "start.json"
    observation_path = tmp_path / "observation.json"
    output_path = tmp_path / "closed.json"
    start_path.write_text(json.dumps(_start_measurement()), encoding="utf-8")
    observation_path.write_text(
        json.dumps(
            {
                "baseline_manual_minutes": 150,
                "review_minutes": 20,
                "relationship_minutes": 10,
                "rejected_or_reworked_candidates": 1,
                "resulting_qualified_actions": 2,
            }
        ),
        encoding="utf-8",
    )

    runner.run(start_path, observation_path, output_path)

    result = json.loads(output_path.read_text(encoding="utf-8"))
    assert result["status"] == "closed"
    assert result["time_saving"]["automated_production_minutes_avoided"] == 120
    assert result["time_saving"]["automation_rate"] == 0.8
    assert result["founder_time_record"]["baseline_manual_minutes"] == 150
    assert result["publication_enabled"] is False


def test_close_runner_rejects_baseline_outside_approved_range(tmp_path: Path) -> None:
    runner = _load_runner()
    start_path = tmp_path / "start.json"
    observation_path = tmp_path / "observation.json"
    output_path = tmp_path / "closed.json"
    start_path.write_text(json.dumps(_start_measurement()), encoding="utf-8")
    observation_path.write_text(
        json.dumps(
            {
                "baseline_manual_minutes": 200,
                "review_minutes": 10,
                "relationship_minutes": 10,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="approved baseline range"):
        runner.run(start_path, observation_path, output_path)


def test_close_runner_rejects_closed_or_publication_enabled_measurement(
    tmp_path: Path,
) -> None:
    runner = _load_runner()
    start_path = tmp_path / "start.json"
    observation_path = tmp_path / "observation.json"
    output_path = tmp_path / "closed.json"
    observation_path.write_text(
        json.dumps(
            {
                "baseline_manual_minutes": 150,
                "review_minutes": 10,
                "relationship_minutes": 10,
            }
        ),
        encoding="utf-8",
    )

    closed = _start_measurement()
    closed["status"] = "closed"
    start_path.write_text(json.dumps(closed), encoding="utf-8")
    with pytest.raises(ValueError, match="open shadow-day"):
        runner.run(start_path, observation_path, output_path)

    publication_enabled = _start_measurement()
    publication_enabled["publication_enabled"] = True
    start_path.write_text(json.dumps(publication_enabled), encoding="utf-8")
    with pytest.raises(ValueError, match="cannot enable publication"):
        runner.run(start_path, observation_path, output_path)
