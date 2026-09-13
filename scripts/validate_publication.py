#!/usr/bin/env python3
"""Fail-closed validation for the public PEACE protocol surface.

This public validator checks only public protocol integrity and generic secret
hygiene. Protected research/IP policy belongs in a private pre-publication gate;
the public repository must not contain a catalogue or reversible fingerprints of
what is meant to remain private.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.0-draft.1"

REQUIRED_FILES = [
    "README.md",
    "LICENSE",
    "NOTICE",
    "GOVERNANCE.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "PUBLICATION_POLICY.md",
    "protocol/PEACE_PROTOCOL_V0.md",
    "schemas/peace-envelope-v0.schema.json",
    "conformance/conformance-v0.json",
]

REQUIRED_INVARIANTS = [
    "ACTOR_IS_AUTHORITY_ROOT",
    "CONTINUITY_ACROSS_REPLACEMENT",
    "CAPABILITY_NE_AUTHORITY",
    "CANDIDATE_NE_DECISION",
    "DISCLOSURE_IS_GOVERNED",
    "NO_DIRECT_EFFECT_PATH",
    "FRESH_AUTHORITY_AT_EFFECT",
    "EVIDENCE_NE_STATE",
    "ROUTING_NE_AUTHORITY",
    "IMPLEMENTATION_NE_PROTOCOL",
    "AUTHORITY_OVER_ACTION_NE_AUTHORITY_OVER_ACTOR",
    "RECOVERY_NE_TRANSFER",
    "REPLICA_NE_SOVEREIGN",
    "UNRESOLVED_IS_GOVERNED",
]

REQUIRED_NEGATIVE_VECTORS = {
    "effect-revoked-001",
    "effect-stale-state-001",
    "effect-action-drift-001",
    "worker-bypass-001",
    "candidate-not-decision-001",
    "routing-not-authority-001",
    "settlement-bypass-001",
    "evidence-not-state-001",
    "admit-unresolved-persist-001",
    "admit-resubmit-bypass-001",
    "authorize-unresolved-binding-001",
    "unresolved-conflict-merge-001",
    "replica-self-promotion-001",
    "replica-conflict-001",
    "recovery-provider-transfer-001",
}

FORBIDDEN_TRACKED_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{30,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
]

TEXT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml", ".py", ".toml"}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def read(path: str) -> str:
    p = ROOT / path
    if not p.is_file():
        fail(f"missing required file: {path}")
    return p.read_text(encoding="utf-8")


def iter_text_files():
    for p in ROOT.rglob("*"):
        if not p.is_file() or ".git" in p.parts or p.stat().st_size > 2_000_000:
            continue
        if p.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            yield p.relative_to(ROOT).as_posix(), p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue


def check_required_files() -> None:
    for path in REQUIRED_FILES:
        if not (ROOT / path).is_file():
            fail(f"missing required file: {path}")


def check_json() -> None:
    try:
        schema = json.loads(read("schemas/peace-envelope-v0.schema.json"))
        vectors = json.loads(read("conformance/conformance-v0.json"))
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON: {exc}")

    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        fail("schema must declare JSON Schema draft 2020-12")
    if schema.get("properties", {}).get("protocol", {}).get("const") != "PEACE/0":
        fail("schema protocol const must be PEACE/0")

    kinds = set(schema.get("properties", {}).get("kind", {}).get("enum", []))
    for required_kind in {"ADMISSION_DECISION", "UNRESOLVED_BINDING"}:
        if required_kind not in kinds:
            fail(f"schema missing required admission kind: {required_kind}")

    ids = {v.get("id") for v in vectors.get("semantic_vectors", [])}
    missing = sorted(REQUIRED_NEGATIVE_VECTORS - ids)
    if missing:
        fail(f"missing mandatory negative conformance vectors: {', '.join(missing)}")


def check_protocol() -> None:
    protocol = read("protocol/PEACE_PROTOCOL_V0.md")
    readme = read("README.md")
    for invariant in REQUIRED_INVARIANTS:
        if invariant not in protocol:
            fail(f"protocol missing constitutional invariant: {invariant}")
    if VERSION not in readme:
        fail(f"README.md must identify draft {VERSION}")


def check_publication_hygiene() -> None:
    for rel, text in iter_text_files():
        for pattern in FORBIDDEN_TRACKED_PATTERNS:
            if pattern.search(text):
                fail(f"possible credential/private key material found in {rel}")


def main() -> None:
    check_required_files()
    check_json()
    check_protocol()
    check_publication_hygiene()
    print(f"PEACE validation PASS: {VERSION}")


if __name__ == "__main__":
    main()
