#!/usr/bin/env python3
"""PortfolioBuildProfileV1 validation and BuildOrderV1 compilation.

This module is the hard boundary between portfolio planning data and Factory OS
build execution.  It deliberately keeps authenticated command/authority context
outside the portfolio profile: an idea/profile can constrain work, but it cannot
self-authorize a repository mutation.

F0 invariants:

* fail closed on incomplete/unknown profile fields;
* bind concept/map/source to an exact 40-hex source SHA;
* require explicit commodity reuse decisions for every configured category;
* require positive evidence for CUSTOM_REQUIRED and NEW_PRIMITIVE_ESTABLISHED;
* compile exactly one bounded BuildOrderV1 per target repository;
* preserve authority metadata exclusively from a separate AuthorityContext;
* emit a deterministic compile receipt that grants no authority.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from lib.build_order_intake import BuildOrderV1, normalize as normalize_build_order, validate as validate_build_order

PROFILE_SCHEMA_VERSION = "portfolio-build-profile.v1"
COMPILE_RECEIPT_VERSION = "portfolio-build-compile-receipt.v1"

PORTFOLIO_CLASSES = {
    "P0_CONTROL_PLANE",
    "P1_PRODUCTION_MACHINERY",
    "P2_OPERATING_CONTEXT",
    "P3_DOMAIN_INTEGRATION",
    "P4_APPLICATION",
    "P5_RESEARCH_STANDARD_EXPERIMENT",
}
PRODUCT_FAMILIES = {"valo", "factory", "os", "applications"}
DELIVERY_STAGES = {"SPECIFIED", "BUILD_READY", "BUILDING", "VALIDATING", "PILOT", "PRODUCTIZED"}
PRIMITIVE_RESULTS = {
    "REUSE_EXISTING",
    "NEW_APPLICATION",
    "NEW_PROFILE",
    "NEW_ADAPTER",
    "NEW_DOMAIN_PACK",
    "NEW_FUNCTION",
    "NEW_WORKFLOW",
    "NEW_PRIMITIVE_ESTABLISHED",
}
REUSE_CATEGORIES = (
    "model_inference",
    "rendering_media",
    "auth_identity_transport",
    "scheduling_queues",
    "storage_database",
    "connectors_api_clients",
    "ui_framework",
    "deployment_runtime",
    "observability",
)
REUSE_DECISIONS = {"REUSE", "NOT_NEEDED", "CUSTOM_REQUIRED"}
RISK_CLASSES = {"A", "B", "C"}

_SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_WILD_SCOPE = {"", ".", "*", "/", "**", "**/*", "/*"}

_TOP_LEVEL_FIELDS = {
    "schema_version",
    "profile_id",
    "source",
    "portfolio_class",
    "product_family",
    "placement",
    "target_capability",
    "target_repos",
    "desired_delivery_stage",
    "primitive_gate",
    "reuse_plan",
    "objective",
    "scope",
    "required_capabilities",
    "dependencies",
    "acceptance_criteria",
    "evidence_refs",
    "risk_class",
    "release_target",
    "requires_independent_qc",
    "requires_receipt",
    "idempotency_key",
    "authority_effect",
}


@dataclass(frozen=True)
class AuthorityContext:
    """Authenticated command metadata supplied by the execution/control plane.

    These values are still metadata in the resulting BuildOrder.  Their presence
    does not itself prove authority; the normal Factory/reht control path remains
    authoritative.
    """

    principal: str
    issued_via: str
    authority_basis: str
    source_ref: str
    issued_at: str
    authority: str = ""
    expires_at: str | None = None
    target_base_ref: str = "main"
    canonical_base_shas: Mapping[str, str] | None = None


@dataclass(frozen=True)
class CompileReceipt:
    schema_version: str
    profile_id: str
    concept_version: str
    map_version: str
    portfolio_source_ref: str
    portfolio_source_sha: str
    authority_source_ref: str
    profile_digest: str
    compiled_at: str
    build_order_ids: tuple[str, ...]
    target_repos: tuple[str, ...]
    receipt_hash: str
    authority_effect: str = "none"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "profile_id": self.profile_id,
            "concept_version": self.concept_version,
            "map_version": self.map_version,
            "portfolio_source_ref": self.portfolio_source_ref,
            "portfolio_source_sha": self.portfolio_source_sha,
            "authority_source_ref": self.authority_source_ref,
            "profile_digest": self.profile_digest,
            "compiled_at": self.compiled_at,
            "build_order_ids": list(self.build_order_ids),
            "target_repos": list(self.target_repos),
            "receipt_hash": self.receipt_hash,
            "authority_effect": self.authority_effect,
        }


@dataclass(frozen=True)
class CompileResult:
    build_orders: tuple[BuildOrderV1, ...]
    receipt: CompileReceipt | None
    problems: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.problems and bool(self.build_orders) and self.receipt is not None


def _clean(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _string_list(value: Any, field_name: str, problems: list[str], *, min_items: int = 0) -> tuple[str, ...]:
    if value is None:
        items: list[Any] = []
    elif isinstance(value, (list, tuple)):
        items = list(value)
    else:
        problems.append(f"{field_name}: must be an array")
        return ()
    normalized = tuple(_clean(item) for item in items if _clean(item))
    if len(normalized) < min_items:
        problems.append(f"{field_name}: requires at least {min_items} item(s)")
    if len(normalized) != len(items):
        problems.append(f"{field_name}: blank items are not allowed")
    return normalized


def _parse_time(value: str) -> datetime | None:
    text = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def canonical_profile_bytes(profile: Mapping[str, Any]) -> bytes:
    """Stable bytes for profile digest/receipt binding."""
    return json.dumps(profile, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def profile_digest(profile: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_profile_bytes(profile)).hexdigest()


def validate_profile(raw: Mapping[str, Any] | None) -> tuple[str, ...]:
    """Deterministically validate F0 build readiness.

    This is intentionally stricter than merely parsing the JSON Schema: the
    Factory compiler requires a delimited scope and exact source SHA in order to
    produce a bounded BuildOrderV1.
    """
    problems: list[str] = []
    if not isinstance(raw, Mapping):
        return ("profile: must be an object",)
    data = dict(raw)

    unknown = sorted(set(data) - _TOP_LEVEL_FIELDS)
    if unknown:
        problems.append("profile: unknown field(s): " + ", ".join(unknown))

    if data.get("schema_version") != PROFILE_SCHEMA_VERSION:
        problems.append(f"schema_version: must equal {PROFILE_SCHEMA_VERSION}")
    if not _clean(data.get("profile_id")):
        problems.append("profile_id: required")

    source = data.get("source")
    if not isinstance(source, Mapping):
        problems.append("source: required object")
        source = {}
    source_allowed = {"idea_id", "concept_version", "map_version", "source_ref", "source_sha", "decision_ref", "mission_id"}
    source_unknown = sorted(set(source) - source_allowed)
    if source_unknown:
        problems.append("source: unknown field(s): " + ", ".join(source_unknown))
    if not _clean(source.get("idea_id")):
        problems.append("source.idea_id: required")
    for key in ("concept_version", "map_version"):
        value = _clean(source.get(key))
        if not _SEMVER_RE.fullmatch(value):
            problems.append(f"source.{key}: semantic version x.y.z required")
    if not _clean(source.get("source_ref")):
        problems.append("source.source_ref: required")
    source_sha = _clean(source.get("source_sha"))
    if not _SHA_RE.fullmatch(source_sha):
        problems.append("source.source_sha: exact lowercase 40-hex SHA required")

    portfolio_class = _clean(data.get("portfolio_class"))
    if portfolio_class not in PORTFOLIO_CLASSES:
        problems.append("portfolio_class: unsupported or legacy/archive class")
    if _clean(data.get("product_family")) not in PRODUCT_FAMILIES:
        problems.append("product_family: unsupported")
    if not _clean(data.get("placement")):
        problems.append("placement: required")

    repos = _string_list(data.get("target_repos"), "target_repos", problems, min_items=1)
    if len(set(repos)) != len(repos):
        problems.append("target_repos: duplicates are not allowed")
    for repo in repos:
        if not _REPO_RE.fullmatch(repo):
            problems.append(f"target_repos: invalid repository {repo!r}")

    if _clean(data.get("desired_delivery_stage")) not in DELIVERY_STAGES:
        problems.append("desired_delivery_stage: unsupported")

    gate = data.get("primitive_gate")
    if not isinstance(gate, Mapping):
        problems.append("primitive_gate: required object")
        gate = {}
    gate_allowed = {"result", "evidence", "new_primitive_owner", "migration_ref", "conformance_ref"}
    gate_unknown = sorted(set(gate) - gate_allowed)
    if gate_unknown:
        problems.append("primitive_gate: unknown field(s): " + ", ".join(gate_unknown))
    gate_result = _clean(gate.get("result"))
    if gate_result not in PRIMITIVE_RESULTS:
        problems.append("primitive_gate.result: unsupported")
    gate_evidence = _string_list(gate.get("evidence"), "primitive_gate.evidence", problems)
    if gate_result == "NEW_PRIMITIVE_ESTABLISHED":
        if not gate_evidence:
            problems.append("primitive_gate.evidence: positive evidence required for new primitive")
        for key in ("new_primitive_owner", "migration_ref", "conformance_ref"):
            if not _clean(gate.get(key)):
                problems.append(f"primitive_gate.{key}: required for NEW_PRIMITIVE_ESTABLISHED")

    reuse_plan = data.get("reuse_plan")
    if not isinstance(reuse_plan, Mapping):
        problems.append("reuse_plan: required object")
        reuse_plan = {}
    missing_reuse = [name for name in REUSE_CATEGORIES if name not in reuse_plan]
    extra_reuse = sorted(set(reuse_plan) - set(REUSE_CATEGORIES))
    if missing_reuse:
        problems.append("reuse_plan: missing categories: " + ", ".join(missing_reuse))
    if extra_reuse:
        problems.append("reuse_plan: unknown categories: " + ", ".join(extra_reuse))
    for name in REUSE_CATEGORIES:
        decision = reuse_plan.get(name)
        if not isinstance(decision, Mapping):
            continue
        allowed = {"decision", "provider_or_component", "reason", "evidence_ref"}
        extra = sorted(set(decision) - allowed)
        if extra:
            problems.append(f"reuse_plan.{name}: unknown field(s): " + ", ".join(extra))
        choice = _clean(decision.get("decision"))
        if choice not in REUSE_DECISIONS:
            problems.append(f"reuse_plan.{name}.decision: unsupported")
        if not _clean(decision.get("reason")):
            problems.append(f"reuse_plan.{name}.reason: required")
        if choice == "CUSTOM_REQUIRED" and not _clean(decision.get("evidence_ref")):
            problems.append(f"reuse_plan.{name}.evidence_ref: required for CUSTOM_REQUIRED")

    if not _clean(data.get("objective")):
        problems.append("objective: required")

    scope = data.get("scope")
    if not isinstance(scope, Mapping):
        problems.append("scope: required object for bounded build intake")
        scope = {}
    scope_allowed = {"paths", "exclude", "out_of_scope"}
    scope_unknown = sorted(set(scope) - scope_allowed)
    if scope_unknown:
        problems.append("scope: unknown field(s): " + ", ".join(scope_unknown))
    paths = _string_list(scope.get("paths"), "scope.paths", problems, min_items=1)
    if not any(path not in _WILD_SCOPE for path in paths):
        problems.append("scope.paths: at least one delimited non-wildcard path required")
    _string_list(scope.get("exclude", []), "scope.exclude", problems)
    _string_list(scope.get("out_of_scope", []), "scope.out_of_scope", problems)

    _string_list(data.get("required_capabilities", []), "required_capabilities", problems)
    _string_list(data.get("dependencies", []), "dependencies", problems)
    _string_list(data.get("acceptance_criteria"), "acceptance_criteria", problems, min_items=1)
    _string_list(data.get("evidence_refs"), "evidence_refs", problems)

    if _clean(data.get("risk_class")) not in RISK_CLASSES:
        problems.append("risk_class: must be A, B or C")
    if not _clean(data.get("idempotency_key")):
        problems.append("idempotency_key: required")
    if data.get("requires_independent_qc", True) is not True:
        problems.append("requires_independent_qc: must be true for Factory intake")
    if data.get("requires_receipt", True) is not True:
        problems.append("requires_receipt: must be true for Factory intake")
    if data.get("authority_effect", "none") != "none":
        problems.append("authority_effect: must be none")

    return tuple(dict.fromkeys(problems))


def validate_authority_context(context: AuthorityContext) -> tuple[str, ...]:
    problems: list[str] = []
    for name in ("principal", "issued_via", "authority_basis", "source_ref", "issued_at"):
        if not _clean(getattr(context, name)):
            problems.append(f"authority_context.{name}: required")
    if context.issued_at and _parse_time(context.issued_at) is None:
        problems.append("authority_context.issued_at: valid ISO-8601 timestamp required")
    if context.expires_at and _parse_time(context.expires_at) is None:
        problems.append("authority_context.expires_at: valid ISO-8601 timestamp required")
    if not _clean(context.target_base_ref):
        problems.append("authority_context.target_base_ref: required")
    for repo, sha in dict(context.canonical_base_shas or {}).items():
        if not _REPO_RE.fullmatch(repo):
            problems.append(f"authority_context.canonical_base_shas: invalid repo {repo!r}")
        if not _SHA_RE.fullmatch(_clean(sha)):
            problems.append(f"authority_context.canonical_base_shas[{repo!r}]: exact lowercase 40-hex SHA required")
    return tuple(dict.fromkeys(problems))


def _risk_hints(profile: Mapping[str, Any]) -> tuple[str, ...]:
    hints = [
        f"portfolio_class={profile['portfolio_class']}",
        f"product_family={profile['product_family']}",
        f"placement={profile['placement']}",
        f"risk_class={profile['risk_class']}",
        f"primitive_gate={profile['primitive_gate']['result']}",
        f"concept_version={profile['source']['concept_version']}",
        f"map_version={profile['source']['map_version']}",
        f"portfolio_source_sha={profile['source']['source_sha']}",
    ]
    target_capability = _clean(profile.get("target_capability"))
    if target_capability:
        hints.append(f"target_capability={target_capability}")
    for category in REUSE_CATEGORIES:
        decision = profile["reuse_plan"][category]
        component = _clean(decision.get("provider_or_component"))
        suffix = f":{component}" if component else ""
        hints.append(f"reuse.{category}={decision['decision']}{suffix}")
    return tuple(hints)


def compile_profile(raw: Mapping[str, Any] | None, authority_context: AuthorityContext) -> CompileResult:
    """Compile one BuildOrderV1 per target repo, or fail closed.

    No field inside ``raw`` may populate principal/issued_via/authority/basis or
    authority source_ref. Those fields come only from ``authority_context``.
    """
    profile_problems = list(validate_profile(raw))
    authority_problems = list(validate_authority_context(authority_context))
    problems = profile_problems + authority_problems
    if problems or not isinstance(raw, Mapping):
        return CompileResult((), None, tuple(dict.fromkeys(problems)))

    profile = dict(raw)
    digest = profile_digest(profile)
    source = dict(profile["source"])
    scope = dict(profile["scope"])
    base_shas = dict(authority_context.canonical_base_shas or {})
    compiled: list[BuildOrderV1] = []

    for repo in profile["target_repos"]:
        key_material = "::".join(
            (
                profile["profile_id"],
                repo,
                source["concept_version"],
                source["map_version"],
                source["source_sha"],
                profile["idempotency_key"],
            )
        )
        suffix = hashlib.sha256(key_material.encode("utf-8")).hexdigest()[:16]
        raw_order = {
            "build_order_id": f"portfolio::{profile['profile_id']}::{suffix}",
            "issued_at": authority_context.issued_at,
            "expires_at": authority_context.expires_at,
            "principal": authority_context.principal,
            "issued_via": authority_context.issued_via,
            "authority": authority_context.authority,
            "authority_basis": authority_context.authority_basis,
            "source_ref": authority_context.source_ref,
            "target_repo": repo,
            "target_base_ref": authority_context.target_base_ref,
            "canonical_base_sha": base_shas.get(repo),
            "objective": profile["objective"],
            "owned_files": [],
            "scope": {
                "paths": list(scope.get("paths", [])),
                "exclude": list(scope.get("exclude", [])),
            },
            "dependencies": list(profile.get("dependencies", [])),
            "acceptance_criteria": list(profile["acceptance_criteria"]),
            "risk_hints": list(_risk_hints(profile)),
            "requires_independent_qc": True,
            "requires_receipt": True,
            "idempotency_key": f"portfolio::{suffix}",
            "authority_effect": "none",
        }
        build_order = normalize_build_order(raw_order)
        bo_problems = validate_build_order(build_order)
        if bo_problems:
            problems.extend(f"{repo}: {problem}" for problem in bo_problems)
        compiled.append(build_order)

    if problems:
        return CompileResult((), None, tuple(dict.fromkeys(problems)))

    compiled_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    receipt_payload = {
        "schema_version": COMPILE_RECEIPT_VERSION,
        "profile_id": profile["profile_id"],
        "concept_version": source["concept_version"],
        "map_version": source["map_version"],
        "portfolio_source_ref": source["source_ref"],
        "portfolio_source_sha": source["source_sha"],
        "authority_source_ref": authority_context.source_ref,
        "profile_digest": digest,
        "compiled_at": compiled_at,
        "build_order_ids": [order.build_order_id for order in compiled],
        "target_repos": [order.target_repo for order in compiled],
        "authority_effect": "none",
    }
    receipt_hash = hashlib.sha256(
        json.dumps(receipt_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    receipt = CompileReceipt(
        schema_version=COMPILE_RECEIPT_VERSION,
        profile_id=profile["profile_id"],
        concept_version=source["concept_version"],
        map_version=source["map_version"],
        portfolio_source_ref=source["source_ref"],
        portfolio_source_sha=source["source_sha"],
        authority_source_ref=authority_context.source_ref,
        profile_digest=digest,
        compiled_at=compiled_at,
        build_order_ids=tuple(order.build_order_id for order in compiled),
        target_repos=tuple(order.target_repo for order in compiled),
        receipt_hash=receipt_hash,
    )
    return CompileResult(tuple(compiled), receipt, ())
