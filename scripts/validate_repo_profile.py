#!/usr/bin/env python3
"""Validate Tofoo- repository profile metadata.

Checks that the canonical AI-first profile (nsolland/Index#338) is internally
consistent across the machine-readable files:

  - repo-manifest.yaml  (authoritative contract)
  - publiccode.yml
  - llms.txt
  - AGENTS.md

Verifies that the research profile separates the epistemic statuses required by
issue #76: hypothesis, mathematical_definition, empirical_observation,
validated_result, falsification_criterion and implementation_claim.

Fails (exit 1) on missing, inconsistent, or stale metadata so CI can block
merges that break the repository profile.
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("PyYAML is required: pip install pyyaml\n")
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parent.parent
STABLE_ID = "valo.tofoo"

REQUIRED_MANIFEST_KEYS = [
    "schema_version",
    "repository",
    "purpose",
    "boundaries",
    "claims",
    "non_claims",
    "interfaces",
    "security",
    "machine_reading",
    "research_profile",
]

REQUIRED_REPOSITORY_KEYS = [
    "id",
    "canonical_name",
    "url",
    "owner",
    "classification",
    "visibility",
    "maturity",
    "support",
    "normative_status",
    "license",
]

REQUIRED_CLAIM_KEYS = [
    "id",
    "statement",
    "epistemic_status",
    "evidence_level",
    "evidence",
]

ALLOWED_EPISTEMIC_STATUSES = {
    "hypothesis",
    "mathematical_definition",
    "empirical_observation",
    "validated_result",
    "falsification_criterion",
    "implementation_claim",
}

ERRORS: list[str] = []


def err(msg: str) -> None:
    ERRORS.append(msg)


def load_yaml(path: Path) -> dict | None:
    if not path.exists():
        err(f"missing {path.name}")
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        err(f"{path.name}: YAML parse error: {exc}")
        return None
    if not isinstance(data, dict):
        err(f"{path.name}: top-level must be a mapping")
        return None
    return data


def check_manifest(manifest_path: Path) -> dict | None:
    manifest = load_yaml(manifest_path)
    if manifest is None:
        return None

    for key in REQUIRED_MANIFEST_KEYS:
        if key not in manifest:
            err(f"{manifest_path.name}: missing required key '{key}'")

    if manifest.get("schema_version") != "1.0":
        err(f"{manifest_path.name}: schema_version must be '1.0'")

    repository = manifest.get("repository", {})
    for key in REQUIRED_REPOSITORY_KEYS:
        if key not in repository:
            err(f"{manifest_path.name}: repository.{key} required")

    if repository.get("id") != STABLE_ID:
        err(f"{manifest_path.name}: repository.id must be '{STABLE_ID}', got {repository.get('id')!r}")

    if repository.get("normative_status") != "informative":
        err(
            f"{manifest_path.name}: repository.normative_status must be 'informative' "
            f"(informative research), got {repository.get('normative_status')!r}"
        )

    purpose = manifest.get("purpose", {})
    for key in ("summary", "owns", "does_not_own"):
        if key not in purpose:
            err(f"{manifest_path.name}: purpose.{key} required")

    claims = manifest.get("claims", [])
    if not claims:
        err(f"{manifest_path.name}: claims must be a non-empty list")
    for claim in claims:
        if not isinstance(claim, dict):
            err(f"{manifest_path.name}: each claim must be a mapping")
            continue
        for key in REQUIRED_CLAIM_KEYS:
            if key not in claim:
                err(f"{manifest_path.name}: claim {claim.get('id', '<no-id>')} missing '{key}'")
        status = claim.get("epistemic_status")
        if status not in ALLOWED_EPISTEMIC_STATUSES:
            err(
                f"{manifest_path.name}: claim {claim.get('id', '<no-id>')} has invalid "
                f"epistemic_status {status!r}; must be one of {sorted(ALLOWED_EPISTEMIC_STATUSES)}"
            )
        if not claim.get("evidence"):
            err(f"{manifest_path.name}: claim {claim.get('id', '<no-id>')} must have non-empty evidence")

    research = manifest.get("research_profile", {})
    categories = research.get("epistemic_categories", {})
    for status in ALLOWED_EPISTEMIC_STATUSES:
        if status not in categories:
            err(f"{manifest_path.name}: research_profile.epistemic_categories must define '{status}'")

    if research.get("runtime_source_of_truth") is not False:
        err(f"{manifest_path.name}: research_profile.runtime_source_of_truth must be false")

    return manifest


def check_cross_consistency(manifest: dict | None) -> None:
    if not manifest:
        return

    pc_path = REPO_ROOT / "publiccode.yml"
    pc = load_yaml(pc_path)
    if pc is not None:
        if pc.get("name") != "Tofoo-":
            err(f"publiccode.yml: name must be 'Tofoo-' to match repo-manifest.yaml, got {pc.get('name')!r}")
        if pc.get("url") != manifest.get("repository", {}).get("url"):
            err("publiccode.yml: url must match repo-manifest.yaml repository.url")
        if not pc.get("legal", {}).get("license"):
            err("publiccode.yml: legal.license required")
        if not pc.get("description", {}).get("en", {}).get("shortDescription"):
            err("publiccode.yml: description.en.shortDescription required")

    llms_path = REPO_ROOT / "llms.txt"
    if llms_path.exists():
        text = llms_path.read_text(encoding="utf-8")
        if STABLE_ID not in text:
            err(f"llms.txt: must reference stable_id '{STABLE_ID}'")
        for status in ("hypothesis", "validated_result", "falsification_criterion"):
            if status not in text:
                err(f"llms.txt: must reference epistemic status '{status}'")
    else:
        err("missing llms.txt")

    agents_path = REPO_ROOT / "AGENTS.md"
    if agents_path.exists():
        text = agents_path.read_text(encoding="utf-8")
        for ref in ("repo-manifest.yaml", "publiccode.yml", "llms.txt", "CLAIM_REGISTRY.md"):
            if ref not in text:
                err(f"AGENTS.md: must reference '{ref}'")
    else:
        err("missing AGENTS.md")

    registry_path = REPO_ROOT / "CLAIM_REGISTRY.md"
    if not registry_path.exists():
        err("missing CLAIM_REGISTRY.md")
    else:
        text = registry_path.read_text(encoding="utf-8")
        for ref in ("Maturity", "Falsification condition"):
            if ref not in text:
                err(f"CLAIM_REGISTRY.md: must contain '{ref}' column/section")

    falsification_path = REPO_ROOT / "docs" / "theories" / "tofoo_falsification_backlog.md"
    if not falsification_path.exists():
        err("missing docs/theories/tofoo_falsification_backlog.md")


def main() -> int:
    manifest_path = REPO_ROOT / "repo-manifest.yaml"
    manifest = check_manifest(manifest_path)
    check_cross_consistency(manifest)

    if ERRORS:
        sys.stderr.write("Repository profile validation FAILED:\n")
        for e in ERRORS:
            sys.stderr.write(f"  - {e}\n")
        return 1

    sys.stdout.write("Repository profile validation OK\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
