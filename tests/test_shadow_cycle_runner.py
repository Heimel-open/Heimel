from __future__ import annotations

import importlib.util
import json
from hashlib import sha256
from pathlib import Path

import pytest


RUNNER_PATH = Path("apps/governed-media-office/run_shadow_cycle.py")


def _load_runner():
    spec = importlib.util.spec_from_file_location("governed_media_shadow_cycle", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _digest(value: bytes) -> str:
    return sha256(value).hexdigest()


def test_cycle_runner_rejects_tampered_source_before_report_validation(tmp_path: Path) -> None:
    runner = _load_runner()
    source_path = tmp_path / "public/source.md"
    approval_path = tmp_path / "public/approval.json"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("Approved source.\n", encoding="utf-8")
    approval_path.write_text('{"approved": true}\n', encoding="utf-8")

    source_ref = {
        "ref": "public/source.md",
        "digest_sha256": _digest(source_path.read_bytes()),
        "version": "v1",
    }
    payload = {
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
        "time_records": [],
    }
    source_path.write_text("Changed after approval.\n", encoding="utf-8")
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "output.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="artifact digest mismatch"):
        runner.run(input_path, output_path, repo_root=tmp_path)
