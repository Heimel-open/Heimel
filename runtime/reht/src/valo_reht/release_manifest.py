"""Build the pinned AI security assurance release manifest."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from .security_assurance import load_manifest, validate_manifest

_ROOT = Path(__file__).resolve().parents[2]
_OVERLAY_PATH = _ROOT / "security" / "ai_security_release_overlay_2026.json"


def build_release_manifest(
    overlay_path: Path | None = None,
) -> dict[str, Any]:
    """Return the closure manifest with the release overlay and exact repo pins."""
    manifest = deepcopy(load_manifest())
    path = overlay_path or _OVERLAY_PATH
    overlay = json.loads(path.read_text(encoding="utf-8"))

    pins = dict(overlay["repository_pins"])
    manifest["repository_pins"] = pins
    manifest["release_policy"] = deepcopy(overlay["release_policy"])
    manifest["validation_snapshots"] = deepcopy(
        overlay.get("validation_snapshots", {})
    )

    risks = {risk["risk_id"]: risk for risk in manifest["risks"]}
    for risk_id, update in overlay.get("risk_updates", {}).items():
        risk = risks[risk_id]
        if "status" in update:
            risk["status"] = update["status"]
        risk["controls"].extend(update.get("add_controls", []))
        risk["evidence"].extend(deepcopy(update.get("add_evidence", [])))
        if "residual_risk" in update:
            risk["residual_risk"] = update["residual_risk"]

    for risk in manifest["risks"]:
        for evidence in risk["evidence"]:
            repo = evidence.get("repo")
            if repo in pins:
                evidence["commit_sha"] = pins[repo]

    validate_manifest(manifest)
    return manifest
