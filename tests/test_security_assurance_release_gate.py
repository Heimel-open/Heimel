from __future__ import annotations

import os
from pathlib import Path

import pytest

from valo_reht.evidence_gate import validate_release_evidence
from valo_reht.release_manifest import build_release_manifest

ROOT = Path(__file__).resolve().parents[1]


def test_release_overlay_keeps_statuses_conservative() -> None:
    manifest = build_release_manifest()
    risks = {risk["risk_id"]: risk for risk in manifest["risks"]}
    assert risks["LLM04"]["status"] == "IMPLEMENTED"
    assert risks["LLM06"]["status"] == "IMPLEMENTED"
    assert risks["ASI04"]["status"] == "IMPLEMENTED"
    assert risks["ASI07"]["status"] == "IMPLEMENTED"
    assert risks["ASI08"]["status"] == "IMPLEMENTED"
    assert manifest["release_policy"]["certification_claim"] is False
    assert manifest["release_policy"]["component_presence_is_not_deployment_proof"] is True


def test_nonlocal_evidence_is_bound_to_release_repository_pin() -> None:
    manifest = build_release_manifest()
    pins = manifest["repository_pins"]
    for risk in manifest["risks"]:
        for evidence in risk["evidence"]:
            repo = evidence["repo"]
            if repo in pins:
                assert evidence["commit_sha"] == pins[repo]


@pytest.mark.skipif(
    os.getenv("VALO_ASSURANCE_RELEASE_GATE") != "1",
    reason="exact dependency snapshots are loaded by the release workflow",
)
def test_exact_pinned_release_evidence_exists_and_resolves() -> None:
    manifest = build_release_manifest()
    release_deps = ROOT / "deps" / "release"
    dependency_roots = {
        repo: release_deps / repo for repo in manifest["repository_pins"]
    }
    validate_release_evidence(
        manifest,
        repo_root=ROOT,
        dependency_roots=dependency_roots,
    )
