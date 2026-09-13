#!/usr/bin/env python3
"""Tofoo Frontier Garden v1 zero-dependency CLI.

This tool validates and reads the informative research registry and can emit a
sterile single-frontier task packet. It does not mutate the registry.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "frontier_garden" / "frontier_registry.json"

AXES = {"WHAT", "WHO", "WHY", "HOW"}
STATUSES = {"OPEN", "ACTIVE", "BLOCKED", "RESOLVED", "RETIRED"}
PRIORITIES = {"HIGH", "MEDIUM", "LOW"}
EPISTEMIC_STATUSES = {
    "hypothesis",
    "mathematical_definition",
    "empirical_observation",
    "validated_result",
    "falsification_criterion",
    "implementation_claim",
}
ROLES = {
    "DERIVATION": (
        "Derive only what follows from the stated frontier state and explicit "
        "source-grounded premises. Mark missing premises and unresolved steps."
    ),
    "SYNAPSE": (
        "Seek non-obvious connections, reframes, candidate primitives or bridges. "
        "Speculation is allowed only when explicitly labeled as hypothetical."
    ),
    "FALSIFIER": (
        "Attack the current understanding. Identify the strongest disconfirming "
        "argument, missing control, invalid assumption or decisive test."
    ),
    "COUNTEREXAMPLE": (
        "Seek a concrete construction, trace, model, dataset or scenario that "
        "would break the current hypothesis or claimed generality."
    ),
    "BRIDGE": (
        "Test whether this frontier and its registered related_frontiers are "
        "manifestations of the same deeper unresolved mechanism. Treat any bridge "
        "as a candidate relation, not an ontology update."
    ),
}

REQUIRED_FRONTIER_FIELDS = {
    "lineage_header",
    "id",
    "title",
    "axes",
    "status",
    "priority",
    "epistemic_status",
    "question",
    "current_understanding",
    "unresolved",
    "falsifier_or_decisive_test",
    "next_gate",
    "source_refs",
    "related_frontiers",
    "lineage",
}


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("registry root must be an object")
    return data


def _require_nonempty_string(value: Any, field: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field}: expected non-empty string")


def validate_registry(data: dict[str, Any], root: Path = ROOT) -> list[str]:
    """Return validation errors. Empty list means structurally valid for Garden v1."""
    errors: list[str] = []

    if data.get("version") != "1.0.0":
        errors.append("version: expected 1.0.0")
    if data.get("repository") != "valo.tofoo":
        errors.append("repository: expected valo.tofoo")
    if data.get("standing") != "INFORMATIVE_RESEARCH_ONLY":
        errors.append("standing: expected INFORMATIVE_RESEARCH_ONLY")

    frontiers = data.get("frontiers")
    if not isinstance(frontiers, list):
        return errors + ["frontiers: expected array"]
    if not frontiers:
        errors.append("frontiers: registry must contain at least one frontier")
        return errors

    ids: list[str] = []
    for index, frontier in enumerate(frontiers):
        prefix = f"frontiers[{index}]"
        if not isinstance(frontier, dict):
            errors.append(f"{prefix}: expected object")
            continue

        missing = REQUIRED_FRONTIER_FIELDS - set(frontier)
        if missing:
            errors.append(f"{prefix}: missing fields {sorted(missing)}")

        frontier_id = frontier.get("id")
        if not isinstance(frontier_id, str) or not re.fullmatch(r"FG-[0-9]{3}", frontier_id):
            errors.append(f"{prefix}.id: expected FG-NNN")
        else:
            ids.append(frontier_id)

        for field in (
            "title",
            "question",
            "current_understanding",
            "unresolved",
            "falsifier_or_decisive_test",
            "next_gate",
        ):
            _require_nonempty_string(frontier.get(field), f"{prefix}.{field}", errors)

        axes = frontier.get("axes")
        if not isinstance(axes, list) or not axes:
            errors.append(f"{prefix}.axes: expected non-empty array")
        elif any(axis not in AXES for axis in axes) or len(set(axes)) != len(axes):
            errors.append(f"{prefix}.axes: invalid or duplicate axis")

        if frontier.get("status") not in STATUSES:
            errors.append(f"{prefix}.status: invalid status")
        if frontier.get("priority") not in PRIORITIES:
            errors.append(f"{prefix}.priority: invalid priority")
        if frontier.get("epistemic_status") not in EPISTEMIC_STATUSES:
            errors.append(f"{prefix}.epistemic_status: invalid Tofoo status")

        contradictions = frontier.get("contradictions", [])
        if not isinstance(contradictions, list) or any(not isinstance(x, str) for x in contradictions):
            errors.append(f"{prefix}.contradictions: expected string array")

        refs = frontier.get("source_refs")
        if not isinstance(refs, list) or not refs:
            errors.append(f"{prefix}.source_refs: expected non-empty array")
        else:
            for ref_index, ref in enumerate(refs):
                ref_prefix = f"{prefix}.source_refs[{ref_index}]"
                if not isinstance(ref, dict):
                    errors.append(f"{ref_prefix}: expected object")
                    continue
                _require_nonempty_string(ref.get("path"), f"{ref_prefix}.path", errors)
                _require_nonempty_string(ref.get("purpose"), f"{ref_prefix}.purpose", errors)
                path_value = ref.get("path")
                if isinstance(path_value, str) and path_value and not (root / path_value).exists():
                    errors.append(f"{ref_prefix}.path: source does not exist: {path_value}")
                claim_id = ref.get("claim_or_test_id")
                if claim_id is not None and not isinstance(claim_id, str):
                    errors.append(f"{ref_prefix}.claim_or_test_id: expected string")

        related = frontier.get("related_frontiers")
        if not isinstance(related, list) or any(not isinstance(x, str) for x in related):
            errors.append(f"{prefix}.related_frontiers: expected string array")
        elif len(set(related)) != len(related):
            errors.append(f"{prefix}.related_frontiers: duplicate id")

        header = frontier.get("lineage_header")
        source_ref_ids = [
            source["path"] + ("#" + source["claim_or_test_id"] if source.get("claim_or_test_id") else "")
            for source in refs or []
            if isinstance(source, dict) and isinstance(source.get("path"), str)
        ]
        if not isinstance(header, dict):
            errors.append(f"{prefix}.lineage_header: expected object")
        else:
            _require_nonempty_string(header.get("origin"), f"{prefix}.lineage_header.origin", errors)
            parents = header.get("parents")
            if not isinstance(parents, list) or any(not isinstance(parent, str) or not parent.strip() for parent in parents):
                errors.append(f"{prefix}.lineage_header.parents: expected string array")
            if header.get("status") not in {"speculative", "question", "evidence-backed"}:
                errors.append(f"{prefix}.lineage_header.status: invalid status")
            evidence_refs = header.get("evidence_refs")
            if evidence_refs != source_ref_ids:
                errors.append(f"{prefix}.lineage_header.evidence_refs: must index source_refs in order")

        lineage = frontier.get("lineage")
        if not isinstance(lineage, dict):
            errors.append(f"{prefix}.lineage: expected object")
        else:
            revision = lineage.get("revision")
            parent = lineage.get("parent_revision")
            if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
                errors.append(f"{prefix}.lineage.revision: expected integer >= 1")
            if parent is not None and (not isinstance(parent, int) or isinstance(parent, bool) or parent < 1):
                errors.append(f"{prefix}.lineage.parent_revision: expected null or integer >= 1")
            if revision == 1 and parent is not None:
                errors.append(f"{prefix}.lineage: revision 1 must have null parent_revision")
            if isinstance(revision, int) and revision > 1 and parent is None:
                errors.append(f"{prefix}.lineage: revision >1 requires parent_revision")
            _require_nonempty_string(lineage.get("change_note"), f"{prefix}.lineage.change_note", errors)

    if len(ids) != len(set(ids)):
        errors.append("frontiers: duplicate frontier id")

    known = set(ids)
    for index, frontier in enumerate(frontiers):
        if not isinstance(frontier, dict):
            continue
        frontier_id = frontier.get("id")
        for related_id in frontier.get("related_frontiers", []):
            if related_id == frontier_id:
                errors.append(f"frontiers[{index}].related_frontiers: self-reference")
            elif related_id not in known:
                errors.append(f"frontiers[{index}].related_frontiers: unknown id {related_id}")

    return errors


def frontier_by_id(data: dict[str, Any], frontier_id: str) -> dict[str, Any]:
    for frontier in data["frontiers"]:
        if frontier.get("id") == frontier_id:
            return frontier
    raise KeyError(frontier_id)


def build_packet(data: dict[str, Any], frontier_id: str, role: str) -> dict[str, Any]:
    if role not in ROLES:
        raise ValueError(f"unknown role: {role}")
    frontier = frontier_by_id(data, frontier_id)
    return {
        "protocol": "tofoo-frontier-garden-v1",
        "registry_version": data["version"],
        "standing": data["standing"],
        "frontier": frontier,
        "role": role,
        "role_instruction": ROLES[role],
        "boundaries": [
            "Treat this as an unresolved research question, not a target answer.",
            "Do not promote speculation, confidence, consensus or novelty into truth.",
            "Distinguish source-supported statements, derivations and hypotheses.",
            "Do not infer runtime authority or consequence-bearing permission.",
            "Return proposals only; this packet cannot update the registry.",
        ],
        "source_refs": frontier["source_refs"],
    }


def cmd_validate(args: argparse.Namespace) -> int:
    data = load_registry(args.registry)
    errors = validate_registry(data, root=ROOT)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"OK: {len(data['frontiers'])} frontiers")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    data = load_registry(args.registry)
    errors = validate_registry(data, root=ROOT)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    rows = data["frontiers"]
    if args.status:
        rows = [row for row in rows if row["status"] == args.status]
    for row in rows:
        axes = "/".join(row["axes"])
        print(f"{row['id']}\t{row['priority']}\t{row['status']}\t{axes}\t{row['title']}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    data = load_registry(args.registry)
    try:
        frontier = frontier_by_id(data, args.frontier_id)
    except KeyError:
        print(f"ERROR: unknown frontier {args.frontier_id}", file=sys.stderr)
        return 2
    print(json.dumps(frontier, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


def cmd_packet(args: argparse.Namespace) -> int:
    data = load_registry(args.registry)
    errors = validate_registry(data, root=ROOT)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    try:
        packet = build_packet(data, args.frontier_id, args.role)
    except KeyError:
        print(f"ERROR: unknown frontier {args.frontier_id}", file=sys.stderr)
        return 2
    print(json.dumps(packet, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tofoo Frontier Garden v1")
    parser.add_argument(
        "--registry",
        type=Path,
        default=REGISTRY_PATH,
        help=f"registry path (default: {REGISTRY_PATH.relative_to(ROOT)})",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="validate the Garden registry")
    validate.set_defaults(func=cmd_validate)

    list_cmd = sub.add_parser("list", help="list registered frontiers")
    list_cmd.add_argument("--status", choices=sorted(STATUSES))
    list_cmd.set_defaults(func=cmd_list)

    show = sub.add_parser("show", help="show one frontier as JSON")
    show.add_argument("frontier_id")
    show.set_defaults(func=cmd_show)

    packet = sub.add_parser("packet", help="emit a sterile single-frontier task packet")
    packet.add_argument("frontier_id")
    packet.add_argument("--role", required=True, choices=sorted(ROLES))
    packet.set_defaults(func=cmd_packet)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
