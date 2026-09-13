"""Validate and independently replay the Case 01 ACT-001 decision contract."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from valo_reht import RealReht

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from generate_act001 import (  # noqa: E402
    DEFAULT_AS001,
    DEFAULT_AS001_SCHEMA,
    EXPECTED_AS001_SHA256,
    EXPECTED_EVIDENCE_IDS,
    EXPECTED_RUNTIME_REASON,
    EXPECTED_UNRESOLVED_CONSTRAINTS,
    _read_json,
    _sha256,
    build_runtime_inputs,
    verify_as001,
)

DEFAULT_ACT001 = HERE / "output" / "ACT-001.json"
DEFAULT_ACT001_SCHEMA = HERE / "ACT-001.schema.json"


def _fail(message: str) -> None:
    raise ValueError(message)


def validate_payload(
    payload: dict[str, Any],
    *,
    as001: dict[str, Any],
    schema: dict[str, Any],
    as001_sha256: str,
) -> None:
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda item: list(item.path))
    if errors:
        rendered = "; ".join(error.message for error in errors[:5])
        _fail(f"ACT-001 schema validation failed: {rendered}")

    if payload["source"]["authority_state_sha256"] != as001_sha256:
        _fail("ACT-001 is not bound to the verified AS-001 bytes")
    if tuple(payload["lineage"]["preserved_evidence_ids"]) != EXPECTED_EVIDENCE_IDS:
        _fail("ACT-001 did not preserve the complete evidence lineage")
    if tuple(payload["blocking_facts_from_as001"]["unresolved_constraints"]) != EXPECTED_UNRESOLVED_CONSTRAINTS:
        _fail("ACT-001 unresolved constraints differ from AS-001")
    if payload["lineage"]["historical_authorization_promoted"] is not False:
        _fail("historical AUTH-001 was promoted to current authority")

    expected_context, expected_action = build_runtime_inputs(
        as001,
        authorization_instant=payload["authorization_instant"],
    )
    runtime_input = payload["runtime_input"]
    if runtime_input["execution_context"] != expected_context:
        _fail("execution context was not derived fail-closed from AS-001")
    if runtime_input["action_contract"] != expected_action:
        _fail("action contract differs from the exact ACT-001 interface mapping")

    replay = RealReht().authorize(
        runtime_input["execution_context"],
        runtime_input["action_contract"],
    )
    actual = payload["runtime_output"]
    expected_output = {
        "decision": replay.decision,
        "reason": replay.reason,
        "clearance_ref": replay.clearance_ref,
        "permit_ref": replay.permit_ref,
        "execution_context_hash": replay.execution_context_hash,
        "effect_commit_permitted": False,
    }
    if actual != expected_output:
        _fail("recorded ACT-001 output does not match an independent RealReht replay")
    if actual["decision"] != "DENY" or actual["reason"] != EXPECTED_RUNTIME_REASON:
        _fail("Case 01 must fail closed at the verified-identity gate")
    if actual["clearance_ref"] is not None or actual["permit_ref"] is not None:
        _fail("DENY must emit neither clearance nor permit")
    if actual["effect_commit_permitted"] is not False:
        _fail("DENY must not permit an effect commit")


def _set_decision_allow(payload: dict[str, Any]) -> None:
    payload["runtime_output"]["decision"] = "ALLOW"


def _set_effect_permitted(payload: dict[str, Any]) -> None:
    payload["runtime_output"]["effect_commit_permitted"] = True


def _forge_permit(payload: dict[str, Any]) -> None:
    payload["runtime_output"]["permit_ref"] = "permit:forged"


def _inject_identity(payload: dict[str, Any]) -> None:
    payload["runtime_input"]["execution_context"]["identity"] = "forged-identity"


def _inject_current_authority(payload: dict[str, Any]) -> None:
    payload["runtime_input"]["execution_context"]["authority"] = [
        {
            "authority_id": "AUTH-001",
            "principal": "forged-actor",
            "capability": "PROCEED_WITH_DISCHARGE",
            "scope": ["*"],
            "status": "ACTIVE",
        }
    ]


def _promote_historical_authorization(payload: dict[str, Any]) -> None:
    payload["lineage"]["historical_authorization_promoted"] = True


def _drop_evidence(payload: dict[str, Any]) -> None:
    payload["lineage"]["preserved_evidence_ids"].remove("REL-001")


def _change_source_hash(payload: dict[str, Any]) -> None:
    payload["source"]["authority_state_sha256"] = "0" * 64


def _change_reason(payload: dict[str, Any]) -> None:
    payload["runtime_output"]["reason"] = "manual approval required"


def _change_context_hash(payload: dict[str, Any]) -> None:
    payload["runtime_output"]["execution_context_hash"] = "0" * 64


def _drop_constraint(payload: dict[str, Any]) -> None:
    payload["runtime_input"]["action_contract"]["constraints"].pop(
        "reassessment_completed_after_EVT-001"
    )


def _change_action(payload: dict[str, Any]) -> None:
    payload["runtime_input"]["action_contract"]["action_id"] = "ACT-999"


NEGATIVE_MUTATIONS: tuple[tuple[str, Callable[[dict[str, Any]], None]], ...] = (
    ("ALLOW substitution", _set_decision_allow),
    ("effect permission on DENY", _set_effect_permitted),
    ("forged permit", _forge_permit),
    ("invented identity", _inject_identity),
    ("historical authority promoted", _inject_current_authority),
    ("historical-promotion flag", _promote_historical_authorization),
    ("evidence lineage collapse", _drop_evidence),
    ("AS-001 hash substitution", _change_source_hash),
    ("runtime reason substitution", _change_reason),
    ("execution-context hash substitution", _change_context_hash),
    ("constraint removal", _drop_constraint),
    ("action substitution", _change_action),
)


def run_negative_tests(
    payload: dict[str, Any],
    *,
    as001: dict[str, Any],
    schema: dict[str, Any],
    as001_sha256: str,
) -> list[str]:
    passed: list[str] = []
    for name, mutate in NEGATIVE_MUTATIONS:
        candidate = copy.deepcopy(payload)
        mutate(candidate)
        try:
            validate_payload(candidate, as001=as001, schema=schema, as001_sha256=as001_sha256)
        except ValueError:
            passed.append(name)
        else:
            _fail(f"negative mutation was accepted: {name}")
    return passed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--act001", type=Path, default=DEFAULT_ACT001)
    parser.add_argument("--schema", type=Path, default=DEFAULT_ACT001_SCHEMA)
    parser.add_argument("--as001", type=Path, default=DEFAULT_AS001)
    parser.add_argument("--as001-schema", type=Path, default=DEFAULT_AS001_SCHEMA)
    args = parser.parse_args()

    as001 = verify_as001(args.as001, args.as001_schema)
    if _sha256(args.as001) != EXPECTED_AS001_SHA256:
        _fail("AS-001 byte identity changed")
    schema = _read_json(args.schema)
    Draft202012Validator.check_schema(schema)
    payload = _read_json(args.act001)
    validate_payload(payload, as001=as001, schema=schema, as001_sha256=_sha256(args.as001))
    passed = run_negative_tests(payload, as001=as001, schema=schema, as001_sha256=_sha256(args.as001))
    print(
        json.dumps(
            {
                "contract": "ACT-001",
                "positive_validation": "PASS",
                "independent_runtime_replay": "PASS",
                "negative_tests_passed": len(passed),
                "negative_tests": passed,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
