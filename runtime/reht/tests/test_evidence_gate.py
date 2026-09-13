from copy import deepcopy
from pathlib import Path

import pytest

from valo_reht.evidence_gate import validate_release_evidence
from valo_reht.security_assurance import ManifestValidationError, load_manifest


def _fixture(tmp_path: Path):
    manifest = deepcopy(load_manifest())
    dependencies = set(manifest["core_repositories"]) - {"valo-reht"}
    pins = {repo: f"{index + 1:040x}" for index, repo in enumerate(sorted(dependencies))}
    roots = {}
    for repo in dependencies:
        root = tmp_path / repo
        root.mkdir()
        (root / "evidence.py").write_text("def test_evidence():\n    pass\n", encoding="utf-8")
        roots[repo] = root
    manifest["repository_pins"] = pins
    for risk in manifest["risks"]:
        for item in risk["evidence"]:
            if item["repo"] in dependencies:
                item["commit_sha"] = pins[item["repo"]]
                item["kind"] = "test"
                item["locator"] = "evidence.py::test_evidence"
    return manifest, roots


def test_exact_evidence_fixture_validates(tmp_path: Path):
    manifest, roots = _fixture(tmp_path)
    validate_release_evidence(
        manifest,
        repo_root=Path(__file__).resolve().parents[1],
        dependency_roots=roots,
    )


def test_changed_revision_fails_validation(tmp_path: Path):
    manifest, roots = _fixture(tmp_path)
    target = next(
        item
        for risk in manifest["risks"]
        for item in risk["evidence"]
        if item["repo"] != "valo-reht"
    )
    target["commit_sha"] = "f" * 40
    with pytest.raises(ManifestValidationError, match="evidence pin mismatch"):
        validate_release_evidence(
            manifest,
            repo_root=Path(__file__).resolve().parents[1],
            dependency_roots=roots,
        )
