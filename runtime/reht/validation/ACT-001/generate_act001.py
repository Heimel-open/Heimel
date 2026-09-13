"""Generate the Case 01 ACT-001 decision through the canonical RealReht runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from valo_reht import RealReht

HERE = Path(__file__).resolve().parent
DEFAULT_AS001 = HERE / "input" / "AS-001.json"
DEFAULT_AS001_SCHEMA = HERE / "input" / "AS-001.schema.v0.2.2.json"
DEFAULT_OUTPUT = HERE / "output" / "ACT-001.json"

EXPECTED_AS001_SHA256 = "4f89c4370d4268521670c0f141b1a0f9d14f869ff069ab0522c876e30c5259d6"
EXPECTED_EVIDENCE_IDS = (
    "PRE-001",
    "ASM-001",
    "AUTH-001",
    "ACT-001",
    "EVT-001",
    "REL-001",
)
EXPECTED_UNRESOLVED_CONSTRAINTS = (
    "clinical_stability_current_after_EVT-001",
    "reassessment_completed_after_EVT-001",
)
EXPECTED_RUNTIME_REASON = "no verified execution identity"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return payload


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _normalize_instant(raw: str | None) -> str:
    if raw is None:
        return datetime.now(UTC).isoformat().replace("+00:00", "Z")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError("authorization instant must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("authorization instant must be timezone-aware")
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def verify_as001(as001_path: Path, schema_path: Path) -> dict[str, Any]:
    """Verify both byte identity and the transferred strict v0.2.2 contract."""
    actual_sha = _sha256(as001_path)
    _require(
        actual_sha == EXPECTED_AS001_SHA256,
        f"AS-001 SHA-256 mismatch: expected {EXPECTED_AS001_SHA256}, got {actual_sha}",
    )

    payload = _read_json(as001_path)
    schema = _read_json(schema_path)
    Draft202012Validator.check_schema(schema)
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda item: list(item.path))
    if errors:
        rendered = "; ".join(error.message for error in errors[:5])
        raise ValueError(f"AS-001 v0.2.2 schema validation failed: {rendered}")

    state = payload["authority_state"]
    boundary = payload["boundary"]
    historical = payload["historical_authorization_evidence"]
    _require(payload["contract_id"] == "AS-001", "wrong authority-state contract")
    _require(payload["case_id"] == "CASE-01", "wrong case")
    _require(payload["source_reliability_finding_id"] == "REL-001", "wrong reliability input")
    _require(state["status"] == "INSUFFICIENT", "Case 01 must remain INSUFFICIENT")
    _require(state["lifecycle"] == "NON_OPERATIVE", "Case 01 must remain NON_OPERATIVE")
    _require(state["is_operative"] is False, "Case 01 authority must not be operative")
    _require(state["premise_acceptance"] is None, "premise acceptance must remain unresolved")
    _require(
        tuple(state["complete_evidence_lineage"]) == EXPECTED_EVIDENCE_IDS,
        "complete evidence lineage changed",
    )
    _require(
        tuple(state["unresolved_constraints"]) == EXPECTED_UNRESOLVED_CONSTRAINTS,
        "unresolved constraints changed",
    )
    _require("IDENTITY_NOT_VERIFIED" in state["reason_codes"], "identity finding missing")
    _require(
        historical["authorization_id"] == "AUTH-001"
        and historical["not_reinterpreted_as_current_execution_authorization"] is True,
        "historical AUTH-001 may not be promoted to current authority",
    )
    _require(boundary["execution_authorization_performed"] is False, "AS-001 crossed its boundary")
    return payload


def build_runtime_inputs(
    as001: dict[str, Any],
    *,
    authorization_instant: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Map AS-001 to REHT without inventing identity or current authority."""
    state = as001["authority_state"]
    action_id, separator, capability = state["action"].partition(":")
    _require(separator == ":" and action_id == "ACT-001" and capability, "malformed ACT-001 action")

    execution_context = {
        "actor": None,
        "identity": None,
        "time": {"now": authorization_instant},
        "authority": [],
        "authority_state": {
            "contract_id": "AS-001",
            "status": state["status"],
            "lifecycle": state["lifecycle"],
            "is_operative": state["is_operative"],
            "subject_id": state["subject_id"],
            "unresolved_constraints": list(state["unresolved_constraints"]),
        },
        "evidence": {
            "source_reliability_finding_id": as001["source_reliability_finding_id"],
            "preserved_evidence_ids": list(state["complete_evidence_lineage"]),
            "historical_authorization_id": "AUTH-001",
            "historical_authorization_is_current": False,
        },
    }
    action_contract = {
        "action_id": action_id,
        "action_type": capability,
        "capability": capability,
        "target": state["resource"],
        "purpose_id": state["purpose"],
        "constraints": dict.fromkeys(state["required_constraint_keys"], True),
        "authority_state_ref": "AS-001",
        "source_evidence_ids": list(state["complete_evidence_lineage"]),
    }
    return execution_context, action_contract


def _provenance() -> dict[str, Any]:
    github_actions = os.getenv("GITHUB_ACTIONS") == "true"
    return {
        "provider": "github-actions" if github_actions else "local",
        "repository": os.getenv("GITHUB_REPOSITORY"),
        "implementation_sha": os.getenv("ACT001_IMPLEMENTATION_SHA", "LOCAL"),
        "workflow_ref": os.getenv("GITHUB_WORKFLOW_REF"),
        "run_id": os.getenv("GITHUB_RUN_ID"),
        "run_attempt": os.getenv("GITHUB_RUN_ATTEMPT"),
    }


def generate_payload(
    as001: dict[str, Any],
    *,
    authorization_instant: str,
    as001_sha256: str = EXPECTED_AS001_SHA256,
) -> dict[str, Any]:
    execution_context, action_contract = build_runtime_inputs(
        as001,
        authorization_instant=authorization_instant,
    )
    result = RealReht().authorize(execution_context, action_contract)
    _require(result.decision == "DENY", f"expected DENY, got {result.decision}")
    _require(result.reason == EXPECTED_RUNTIME_REASON, f"unexpected runtime reason: {result.reason}")
    _require(result.clearance_ref is None, "DENY must not emit clearance")
    _require(result.permit_ref is None, "DENY must not emit execution permit")

    state = as001["authority_state"]
    return {
        "contract_id": "ACT-001",
        "schema_version": "valo-reht.execution-authorization-decision.v0.1.0",
        "case_id": "CASE-01",
        "authorization_instant": authorization_instant,
        "source": {
            "authority_state_contract_id": "AS-001",
            "authority_state_schema_version": as001["schema_version"],
            "authority_state_sha256": as001_sha256,
            "authority_state_repository": "esklavounou/Authority-Instrumentation-",
            "authority_state_implementation_sha": "50bef6179fd8ecd8bbbba3aedb7eee25d743b55f",
            "authority_state_workflow_run_id": "32521022710",
        },
        "runtime_input": {
            "execution_context": execution_context,
            "action_contract": action_contract,
        },
        "runtime_output": {
            "decision": result.decision,
            "reason": result.reason,
            "clearance_ref": result.clearance_ref,
            "permit_ref": result.permit_ref,
            "execution_context_hash": result.execution_context_hash,
            "effect_commit_permitted": False,
        },
        "blocking_facts_from_as001": {
            "authority_state_status": state["status"],
            "authority_state_lifecycle": state["lifecycle"],
            "identity_verified": False,
            "current_operative_authority_present": False,
            "unresolved_constraints": list(state["unresolved_constraints"]),
        },
        "lineage": {
            "preserved_evidence_ids": list(state["complete_evidence_lineage"]),
            "source_authority_state_contract_id": "AS-001",
            "source_reliability_finding_id": "REL-001",
            "historical_authorization_id": "AUTH-001",
            "historical_authorization_promoted": False,
        },
        "boundary": {
            "authorization_owner": "VALO_REHT",
            "authority_state_owner": "AUTHORITY_INSTRUMENTATION",
            "effect_executed": False,
            "downstream_execution_requires_allow_and_permit": True,
        },
        "execution_provenance": _provenance(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--as001", type=Path, default=DEFAULT_AS001)
    parser.add_argument("--as001-schema", type=Path, default=DEFAULT_AS001_SCHEMA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--authorization-instant")
    args = parser.parse_args()

    instant = _normalize_instant(args.authorization_instant)
    as001 = verify_as001(args.as001, args.as001_schema)
    payload = generate_payload(as001, authorization_instant=instant, as001_sha256=_sha256(args.as001))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "contract_id": payload["contract_id"],
                "decision": payload["runtime_output"]["decision"],
                "reason": payload["runtime_output"]["reason"],
                "permit_ref": payload["runtime_output"]["permit_ref"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
