#!/usr/bin/env python3
"""Deterministic security-evidence gate for VALO Factory."""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class MatrixResult:
    status: str
    categories: tuple[str, ...]
    required_evidence: tuple[str, ...]
    missing_evidence: tuple[str, ...]


def _matches(path: str, pattern: str) -> bool:
    normalized = path.strip().lstrip("./")
    pattern = pattern.lstrip("./")
    if fnmatch.fnmatch(normalized, pattern):
        return True
    if pattern.startswith("**/"):
        return fnmatch.fnmatch(normalized, pattern[3:])
    return False


def classify_paths(paths: Iterable[str], policy: dict[str, Any]) -> tuple[str, ...]:
    categories: set[str] = set()
    for category, patterns in policy.get("sensitive_paths", {}).items():
        if any(_matches(path, pattern) for path in paths for pattern in patterns):
            categories.add(category)
    return tuple(sorted(categories))


def required_evidence(categories: Iterable[str], policy: dict[str, Any]) -> tuple[str, ...]:
    requirements = set(policy.get("required_evidence", {}).get("default", []))
    for category in categories:
        requirements.update(policy.get("required_evidence", {}).get(category, []))
    return tuple(sorted(requirements))


def evaluate(
    changed_paths: Iterable[str],
    manifest: dict[str, Any] | None,
    policy: dict[str, Any],
) -> MatrixResult:
    categories = classify_paths(changed_paths, policy)
    required = required_evidence(categories, policy)

    if not categories:
        return MatrixResult("PASS", categories, required, ())

    if manifest is None:
        return MatrixResult("FAIL", categories, required, required)

    allowed = set(policy.get("manifest", {}).get("allowed_statuses", ["PASS"]))
    evidence = manifest.get("evidence", {})
    missing = tuple(
        item for item in required
        if not isinstance(evidence.get(item), dict)
        or evidence[item].get("status") not in allowed
        or not evidence[item].get("proof")
    )
    return MatrixResult("PASS" if not missing else "FAIL", categories, required, missing)
