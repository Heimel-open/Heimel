from __future__ import annotations

import json
from pathlib import Path

import scripts.repo_traction as tracker


def test_collect_includes_public_and_traffic_metrics(monkeypatch):
    responses = {
        "/repos/Heimel-open/Heimel": {
            "stargazers_count": 3,
            "forks_count": 2,
            "subscribers_count": 1,
            "open_issues_count": 4,
        },
        "/repos/Heimel-open/Heimel/traffic/views": {"count": 20, "uniques": 7, "views": []},
        "/repos/Heimel-open/Heimel/traffic/clones": {"count": 9, "uniques": 4, "clones": []},
        "/repos/Heimel-open/Heimel/traffic/popular/referrers": [{"referrer": "example.com", "count": 5, "uniques": 3}],
        "/repos/Heimel-open/Heimel/traffic/popular/paths": [{"path": "/Heimel-open/Heimel", "title": "Heimel", "count": 8, "uniques": 4}],
    }

    def fake_get(path: str, token: str):
        assert token == "token"
        return responses[path]

    def fake_optional(path: str, token: str):
        if path.startswith("/search/issues"):
            assert "-author%3Ansolland" in path
            return {"total_count": 6}, None
        return fake_get(path, token), None

    monkeypatch.setattr(tracker, "_get", fake_get)
    monkeypatch.setattr(tracker, "_optional", fake_optional)

    snapshot = tracker.collect("Heimel-open/Heimel", "token")

    assert snapshot["stars"] == 3
    assert snapshot["forks"] == 2
    assert snapshot["watchers"] == 1
    assert snapshot["views_14d"]["uniques"] == 7
    assert snapshot["clones_14d"]["uniques"] == 4
    assert snapshot["external_open_items"] == 6
    assert snapshot["traffic_complete"] is True
    assert snapshot["traffic_errors"] == {}


def test_collect_records_missing_privileged_traffic_without_losing_public_metrics(monkeypatch):
    monkeypatch.setattr(
        tracker,
        "_get",
        lambda path, token: {
            "stargazers_count": 0,
            "forks_count": 0,
            "subscribers_count": 0,
            "open_issues_count": 1,
        },
    )

    def fake_optional(path: str, token: str):
        if path.startswith("/search/issues"):
            return {"total_count": 0}, None
        return None, "HTTP 403"

    monkeypatch.setattr(tracker, "_optional", fake_optional)

    snapshot = tracker.collect("Heimel-open/Heimel", "token")

    assert snapshot["stars"] == 0
    assert snapshot["external_open_items"] == 0
    assert snapshot["traffic_complete"] is False
    assert snapshot["traffic_errors"]["views"] == "HTTP 403"


def test_append_snapshot_is_jsonl(tmp_path: Path):
    output = tmp_path / "telemetry" / "repo_traction.jsonl"
    tracker.append_snapshot(output, {"stars": 1})
    tracker.append_snapshot(output, {"stars": 2})

    lines = output.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["stars"] for line in lines] == [1, 2]
