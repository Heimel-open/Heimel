from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from valo_reht import RealReht

ACT001_DIR = Path(__file__).resolve().parents[1] / "validation" / "ACT-001"
sys.path.insert(0, str(ACT001_DIR))

from generate_act001 import (  # noqa: E402
    DEFAULT_AS001,
    DEFAULT_AS001_SCHEMA,
    EXPECTED_AS001_SHA256,
    EXPECTED_EVIDENCE_IDS,
    EXPECTED_RUNTIME_REASON,
    _read_json,
    _sha256,
    build_runtime_inputs,
    generate_payload,
    verify_as001,
)
from validate_act001 import run_negative_tests, validate_payload  # noqa: E402

FIXED_AUTHORIZATION_INSTANT = "2026-08-21T20:00:00Z"


def _fixtures() -> tuple[dict, dict]:
    as001 = verify_as001(DEFAULT_AS001, DEFAULT_AS001_SCHEMA)
    schema = _read_json(ACT001_DIR / "ACT-001.schema.json")
    Draft202012Validator.check_schema(schema)
    return as001, schema


def test_transferred_as001_has_exact_bytes_and_strict_contract() -> None:
    as001, _ = _fixtures()
    assert _sha256(DEFAULT_AS001) == EXPECTED_AS001_SHA256
    assert as001["authority_state"]["status"] == "INSUFFICIENT"
    assert as001["authority_state"]["lifecycle"] == "NON_OPERATIVE"
    assert as001["authority_state"]["is_operative"] is False


def test_act001_runs_real_reht_and_fails_closed() -> None:
    as001, schema = _fixtures()
    payload = generate_payload(as001, authorization_instant=FIXED_AUTHORIZATION_INSTANT)
    validate_payload(payload, as001=as001, schema=schema, as001_sha256=EXPECTED_AS001_SHA256)

    result = payload["runtime_output"]
    assert result["decision"] == "DENY"
    assert result["reason"] == EXPECTED_RUNTIME_REASON
    assert result["clearance_ref"] is None
    assert result["permit_ref"] is None
    assert result["effect_commit_permitted"] is False


def test_historical_auth001_is_evidence_not_current_authority() -> None:
    as001, _ = _fixtures()
    context, _ = build_runtime_inputs(as001, authorization_instant=FIXED_AUTHORIZATION_INSTANT)
    assert context["authority"] == []
    assert context["evidence"]["historical_authorization_id"] == "AUTH-001"
    assert context["evidence"]["historical_authorization_is_current"] is False
    assert tuple(context["evidence"]["preserved_evidence_ids"]) == EXPECTED_EVIDENCE_IDS


def test_identity_alone_cannot_replace_missing_current_authority() -> None:
    as001, _ = _fixtures()
    context, action = build_runtime_inputs(as001, authorization_instant=FIXED_AUTHORIZATION_INSTANT)
    context = copy.deepcopy(context)
    context["actor"] = "verified-test-actor"
    context["identity"] = "verified-test-identity"

    result = RealReht().authorize(context, action)
    assert result.decision == "DENY"
    assert result.reason == "no active authority for PROCEED_WITH_DISCHARGE"
    assert result.clearance_ref is None
    assert result.permit_ref is None


def test_fixed_vector_is_repeatable() -> None:
    as001, _ = _fixtures()
    first = generate_payload(as001, authorization_instant=FIXED_AUTHORIZATION_INSTANT)
    second = generate_payload(as001, authorization_instant=FIXED_AUTHORIZATION_INSTANT)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_negative_contract_mutations_are_rejected() -> None:
    as001, schema = _fixtures()
    payload = generate_payload(as001, authorization_instant=FIXED_AUTHORIZATION_INSTANT)
    passed = run_negative_tests(
        payload,
        as001=as001,
        schema=schema,
        as001_sha256=EXPECTED_AS001_SHA256,
    )
    assert len(passed) == 12


def test_tampered_as001_is_rejected_before_runtime(tmp_path: Path) -> None:
    as001 = _read_json(DEFAULT_AS001)
    as001["authority_state"]["is_operative"] = True
    tampered = tmp_path / "AS-001.json"
    tampered.write_text(json.dumps(as001, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        verify_as001(tampered, DEFAULT_AS001_SCHEMA)
