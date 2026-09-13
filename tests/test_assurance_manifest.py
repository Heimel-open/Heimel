from __future__ import annotations

from copy import deepcopy

import pytest

from valo_reht.security_assurance import (
    ManifestValidationError,
    load_manifest,
    validate_local_test_references,
    validate_manifest,
)


def test_manifest_covers_all_llm_and_agentic_risks() -> None:
    manifest = validate_manifest(load_manifest())
    ids = {risk["risk_id"] for risk in manifest["risks"]}
    expected = {f"LLM{i:02d}" for i in range(1, 11)} | {
        f"ASI{i:02d}" for i in range(1, 11)
    }
    assert ids == expected


def test_every_risk_has_owner_control_evidence_and_residual_risk() -> None:
    manifest = validate_manifest(load_manifest())
    for risk in manifest["risks"]:
        assert risk["owners"]
        assert risk["controls"]
        assert risk["evidence"]
        assert risk["residual_risk"].strip()
        assert risk["external_dependencies_required"] is False


def test_local_test_references_resolve() -> None:
    manifest = validate_manifest(load_manifest())
    validate_local_test_references(manifest)


def test_proven_without_executable_test_is_rejected() -> None:
    manifest = deepcopy(load_manifest())
    risk = next(item for item in manifest["risks"] if item["risk_id"] == "LLM03")
    risk["evidence"] = [
        {
            "repo": "valo-reht",
            "kind": "implementation",
            "locator": "src/valo_reht/reht.py",
        }
    ]
    with pytest.raises(
        ManifestValidationError, match="PROVEN requires an executable test"
    ):
        validate_manifest(manifest)


def test_unknown_control_owner_is_rejected() -> None:
    manifest = deepcopy(load_manifest())
    manifest["risks"][0]["owners"] = ["unknown-component"]
    with pytest.raises(ManifestValidationError, match="invalid core owner"):
        validate_manifest(manifest)


def test_mandatory_external_dependency_is_rejected() -> None:
    manifest = deepcopy(load_manifest())
    manifest["risks"][0]["external_dependencies_required"] = True
    with pytest.raises(
        ManifestValidationError, match="external dependencies cannot be mandatory"
    ):
        validate_manifest(manifest)


def test_orphaned_risk_without_evidence_is_rejected() -> None:
    manifest = deepcopy(load_manifest())
    manifest["risks"][0]["evidence"] = []
    with pytest.raises(ManifestValidationError, match="evidence is required"):
        validate_manifest(manifest)


def test_blank_residual_risk_is_rejected() -> None:
    manifest = deepcopy(load_manifest())
    manifest["risks"][0]["residual_risk"] = ""
    with pytest.raises(ManifestValidationError, match="residual_risk is required"):
        validate_manifest(manifest)
