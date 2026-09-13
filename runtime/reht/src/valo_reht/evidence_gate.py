"""Pinned evidence gate for the AI assurance manifest."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from .security_assurance import ManifestValidationError, validate_manifest

LOCAL_REPOSITORY = "valo-reht"
_SHA_RE = re.compile(r"^[a-f0-9]{40}$")


def validate_release_evidence(
    manifest: dict[str, Any],
    *,
    repo_root: Path,
    dependency_roots: dict[str, Path],
) -> dict[str, Any]:
    validate_manifest(manifest)
    errors: list[str] = []
    core = set(manifest["core_repositories"])
    required_pins = core - {LOCAL_REPOSITORY}
    pins = manifest.get("repository_pins")
    if not isinstance(pins, dict):
        raise ManifestValidationError(["repository_pins is required"])
    if set(pins) != required_pins:
        errors.append("repository_pins must cover non-local core repositories exactly")
    for repo, sha in pins.items():
        if not isinstance(sha, str) or _SHA_RE.fullmatch(sha) is None:
            errors.append(f"invalid repository pin for {repo}")
    if set(dependency_roots) != required_pins:
        errors.append("dependency roots must match repository pins exactly")

    for risk in manifest["risks"]:
        for evidence in risk["evidence"]:
            repo = evidence["repo"]
            if repo not in core:
                continue
            if repo == LOCAL_REPOSITORY:
                root = repo_root
            else:
                if evidence.get("commit_sha") != pins.get(repo):
                    errors.append(f"{risk['risk_id']}: evidence pin mismatch for {repo}")
                root = dependency_roots.get(repo)
                if root is None:
                    continue
            _check_locator(risk["risk_id"], evidence, root, errors)

    if errors:
        raise ManifestValidationError(errors)
    return manifest


def _check_locator(
    risk_id: str,
    evidence: dict[str, Any],
    root: Path,
    errors: list[str],
) -> None:
    locator = str(evidence["locator"])
    path_text, separator, function_name = locator.partition("::")
    path = root / path_text
    if not path.exists():
        errors.append(f"{risk_id}: missing evidence path {path_text}")
        return
    if evidence["kind"] != "test":
        return
    if not separator or not function_name or not path.is_file():
        errors.append(f"{risk_id}: invalid executable test locator {locator}")
        return
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    functions = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    if function_name not in functions:
        errors.append(f"{risk_id}: missing executable test {locator}")
