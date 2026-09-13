from __future__ import annotations

import importlib.util
import json
from hashlib import sha256
from pathlib import Path

import pytest


RUNNER_PATH = Path("apps/governed-media-office/run_shadow_day.py")


def _load_runner():
    spec = importlib.util.spec_from_file_location("governed_media_shadow_day", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _digest(value: bytes) -> str:
    return sha256(value).hexdigest()


def _manifest(repo_root: Path) -> dict:
    source_path = repo_root / "public/source.md"
    approval_path = repo_root / "public/approval.json"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("Approved public source.\n", encoding="utf-8")
    approval_path.write_text('{"approved": true}\n', encoding="utf-8")

    source_ref = {
        "ref": "public/source.md",
        "digest_sha256": _digest(source_path.read_bytes()),
        "version": "v1",
    }
    return {
        "schema_version": "governed-media-approved-signals/v1",
        "cycle_id": "cycle-1",
        "day": 1,
        "publication_enabled": False,
        "approved_signals": [
            {
                "source_type": "founder_note",
                "source_artifact_ref": source_ref,
                "confidentiality": "public",
                "public_use_approval": {
                    "approval_ref": {
                        "ref": "public/approval.json",
                        "digest_sha256": _digest(approval_path.read_bytes()),
                        "version": "v1",
                    },
                    "approved_by": "founder",
                    "approved_at": "2026-07-28T18:00:00Z",
                    "allowed_channels": ["linkedin"],
                    "expires_at": "2026-08-04T23:59:59Z",
                    "revoked": False,
                },
                "draft": {
                    "signal_id": "signal-1",
                    "observed_at": "2026-07-28T18:01:00Z",
                    "candidate_type": "post",
                    "theme_key": "execution-governance",
                    "canonical_asset_id": "asset-1",
                    "campaign_id": "campaign-1",
                    "account_identity": "founder:linkedin",
                    "audience_intent_id": "enterprise",
                    "rendered_content": "A governed shadow candidate.",
                    "source_refs": [source_ref],
                    "claim_bindings": [],
                    "ai_production_disclosure": "AI-assisted. Human review required.",
                    "why_now": "The implementation is ready for shadow evaluation.",
                    "relationship_objective": "Create a qualified technical conversation.",
                    "risk_class": "medium",
                    "strategic_relevance": 0.9,
                    "evidence_strength": 0.9,
                    "novelty": 0.9,
                    "timeliness": 0.9,
                    "audience_fit": 0.9,
                    "relationship_value": 0.9,
                    "authority_risk": 0.1,
                    "founder_effort_minutes": 5,
                    "named_relationship": False,
                    "sensitive": False,
                },
            }
        ],
    }


def test_single_day_runner_builds_publication_disabled_queue(tmp_path: Path) -> None:
    runner = _load_runner()
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "output.json"
    input_path.write_text(json.dumps(_manifest(tmp_path)), encoding="utf-8")

    runner.run(input_path, output_path, repo_root=tmp_path)

    result = json.loads(output_path.read_text(encoding="utf-8"))
    assert result["cycle_id"] == "cycle-1"
    assert result["day"] == 1
    assert result["measurement_status"] == "open"
    assert result["publication_enabled"] is False
    assert result["queue"]["publication_enabled"] is False
    assert len(result["queue"]["post_candidates"]) == 1
    assert result["queue"]["comment_candidates"] == []


def test_single_day_runner_rejects_publication_enablement(tmp_path: Path) -> None:
    runner = _load_runner()
    manifest = _manifest(tmp_path)
    manifest["publication_enabled"] = True
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "output.json"
    input_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="cannot enable publication"):
        runner.run(input_path, output_path, repo_root=tmp_path)


def test_single_day_runner_rejects_changed_source_content(tmp_path: Path) -> None:
    runner = _load_runner()
    manifest = _manifest(tmp_path)
    (tmp_path / "public/source.md").write_text("Changed after approval.\n", encoding="utf-8")
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "output.json"
    input_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="artifact digest mismatch"):
        runner.run(input_path, output_path, repo_root=tmp_path)
