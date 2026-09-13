"""Executable validator for the VALO 2026 AI security assurance manifest."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

EXPECTED_LLM_IDS = {f"LLM{i:02d}" for i in range(1, 11)}
EXPECTED_AGENTIC_IDS = {f"ASI{i:02d}" for i in range(1, 11)}
EXPECTED_STATUSES = {"PROVEN", "IMPLEMENTED", "PARTIAL", "NOT_EVIDENCED"}
EVIDENCE_KINDS = {"test", "implementation", "receipt", "external"}
DEFAULT_MANIFEST_PATH = (
    Path(__file__).resolve().parents[2] / "security" / "ai_security_closure_2026.json"
)


class ManifestValidationError(ValueError):
    """Raised when the assurance manifest makes an unsupported claim."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = tuple(errors)
        super().__init__("; ".join(errors))


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    manifest_path = path or DEFAULT_MANIFEST_PATH
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if manifest.get("schema_id") != "valo.security.assurance-closure.v1":
        errors.append("invalid schema_id")
    if set(manifest.get("allowed_status", ())) != EXPECTED_STATUSES:
        errors.append("allowed_status must match the canonical status set")
    if manifest.get("source_policy", {}).get("certification_claim") is not False:
        errors.append("manifest must not make a blanket certification claim")

    core = set(manifest.get("core_repositories", ()))
    optional = set(manifest.get("optional_external_evidence_providers", ()))
    risks = manifest.get("risks")
    if not isinstance(risks, list):
        raise ManifestValidationError(["risks must be a list"])

    ids = [risk.get("risk_id") for risk in risks if isinstance(risk, dict)]
    if len(ids) != len(set(ids)):
        errors.append("risk_id values must be unique")
    llm_ids = {
        risk_id
        for risk_id in ids
        if isinstance(risk_id, str) and risk_id.startswith("LLM")
    }
    asi_ids = {
        risk_id
        for risk_id in ids
        if isinstance(risk_id, str) and risk_id.startswith("ASI")
    }
    if llm_ids != EXPECTED_LLM_IDS:
        errors.append("manifest must cover LLM01 through LLM10 exactly")
    if asi_ids != EXPECTED_AGENTIC_IDS:
        errors.append("manifest must cover ASI01 through ASI10 exactly")

    for risk in risks:
        if not isinstance(risk, dict):
            errors.append("risk entries must be objects")
            continue
        risk_id = str(risk.get("risk_id", "<missing>"))
        status = risk.get("status")
        if status not in EXPECTED_STATUSES:
            errors.append(f"{risk_id}: invalid status")
        if not str(risk.get("title", "")).strip():
            errors.append(f"{risk_id}: missing title")
        owners = risk.get("owners")
        if not isinstance(owners, list) or not owners:
            errors.append(f"{risk_id}: at least one control owner is required")
        else:
            unknown_owners = set(owners) - core
            if unknown_owners:
                errors.append(
                    f"{risk_id}: invalid core owner(s): {sorted(unknown_owners)}"
                )
        controls = risk.get("controls")
        if not isinstance(controls, list) or not controls:
            errors.append(f"{risk_id}: at least one control is required")
        if not str(risk.get("residual_risk", "")).strip():
            errors.append(f"{risk_id}: residual_risk is required")
        if risk.get("external_dependencies_required") is not False:
            errors.append(f"{risk_id}: external dependencies cannot be mandatory")

        evidence = risk.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{risk_id}: evidence is required")
            continue
        has_executable_test = False
        for item in evidence:
            if not isinstance(item, dict):
                errors.append(f"{risk_id}: evidence entries must be objects")
                continue
            repo = item.get("repo")
            kind = item.get("kind")
            locator = str(item.get("locator", ""))
            if repo not in core | optional:
                errors.append(f"{risk_id}: unknown evidence repository {repo!r}")
            if kind not in EVIDENCE_KINDS:
                errors.append(f"{risk_id}: invalid evidence kind {kind!r}")
            if not locator.strip():
                errors.append(f"{risk_id}: empty evidence locator")
            if repo in optional and kind != "external":
                errors.append(
                    f"{risk_id}: optional external evidence must be marked external"
                )
            if kind == "test" and "::" in locator:
                has_executable_test = True
        if status == "PROVEN" and not has_executable_test:
            errors.append(f"{risk_id}: PROVEN requires an executable test reference")

    if errors:
        raise ManifestValidationError(errors)
    return manifest


def validate_local_test_references(
    manifest: dict[str, Any], repo_root: Path | None = None
) -> None:
    root = repo_root or Path(__file__).resolve().parents[2]
    errors: list[str] = []
    for risk in manifest["risks"]:
        for evidence in risk["evidence"]:
            if evidence["repo"] != "valo-reht" or evidence["kind"] != "test":
                continue
            locator = evidence["locator"]
            path_text, separator, function_name = locator.partition("::")
            path = root / path_text
            if not path.is_file():
                errors.append(f"{risk['risk_id']}: missing local test file {path_text}")
                continue
            if not separator:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            functions = {
                node.name
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            if function_name not in functions:
                errors.append(f"{risk['risk_id']}: missing local test {locator}")
    if errors:
        raise ManifestValidationError(errors)


def validate_default_manifest() -> dict[str, Any]:
    manifest = validate_manifest(load_manifest())
    validate_local_test_references(manifest)
    return manifest
