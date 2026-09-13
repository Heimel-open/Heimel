from __future__ import annotations

from importlib import import_module
from pathlib import Path

from valo_reht import RealReht

owasp = import_module("valo_reht.owasp_llm_2026")


BASE_CTX = {
    "actor": "agent-1",
    "identity": "id-agent-1",
    "time": {"now": "2026-08-13T16:00:00+00:00"},
    "authority": [
        {
            "authority_id": "auth-1",
            "principal": "agent-1",
            "capability": "CAPABILITY_A",
            "scope": ["target-a"],
            "constraints": {"purpose_id": "purpose-a"},
            "validity": {
                "valid_from": "2026-08-13T15:00:00+00:00",
                "valid_until": "2026-08-13T17:00:00+00:00",
            },
            "status": "ACTIVE",
        }
    ],
}


def _contract(**extra) -> dict:
    contract = {
        "capability": "CAPABILITY_A",
        "target": "target-a",
        "action_type": "ACTION_A",
        "purpose_id": "purpose-a",
    }
    contract.update(extra)
    return contract


def test_crosswalk_is_complete_and_ordered() -> None:
    expected = [f"LLM{i:02d}" for i in range(1, 11)]
    assert [risk.risk_id for risk in owasp.OWASP_LLM_2026] == expected
    assert set(owasp.OWASP_LLM_2026_BY_ID) == set(expected)


def test_every_risk_has_boundary_control_evidence_and_negative_acceptance() -> None:
    for risk in owasp.OWASP_LLM_2026:
        assert risk.reht_role in {"PRIMARY", "CONTRIBUTING", "EXTERNAL"}
        assert risk.boundaries and risk.controls and risk.evidence and risk.negative_tests


def test_crosswalk_does_not_claim_reht_owns_external_risk_classes() -> None:
    for risk_id in ("LLM04", "LLM06", "LLM08"):
        risk = owasp.OWASP_LLM_2026_BY_ID[risk_id]
        assert risk.reht_role == "EXTERNAL"
        assert risk.residual_or_external


def test_all_repo_acceptance_references_resolve() -> None:
    for risk in owasp.OWASP_LLM_2026:
        for reference in risk.negative_tests:
            if reference.startswith("external:"):
                continue
            path, separator, test_name = reference.partition("::")
            assert separator == "::" and test_name.startswith("test_")
            assert Path(path).is_file(), reference
            assert f"def {test_name}(" in Path(path).read_text(encoding="utf-8"), reference


def test_llm01_injected_capability_cannot_create_authority() -> None:
    result = RealReht().authorize(BASE_CTX, _contract(capability="CAPABILITY_B"))
    assert result.decision == "DENY"
    assert result.permit_ref is None


def test_llm01_injected_target_cannot_escape_scope() -> None:
    result = RealReht().authorize(BASE_CTX, _contract(target="target-b"))
    assert result.decision == "DENY"
    assert result.permit_ref is None


def test_llm02_cross_scope_action_is_denied() -> None:
    assert RealReht().authorize(BASE_CTX, _contract(target="other-scope")).decision == "DENY"


def test_llm03_excess_tool_functionality_cannot_expand_capability() -> None:
    result = RealReht().authorize(BASE_CTX, _contract(capability="CAPABILITY_B", action_type="ACTION_B"))
    assert result.decision == "DENY"


def test_llm09_retrieved_content_cannot_expand_action_scope() -> None:
    candidate = _contract(target="retrieved-target")
    assert RealReht().authorize(BASE_CTX, candidate).decision == "DENY"


def test_llm10_changed_model_output_invalidates_prior_permit_binding() -> None:
    original = RealReht().authorize(BASE_CTX, _contract(candidate_value="a"))
    changed = RealReht().authorize(BASE_CTX, _contract(candidate_value="b"))
    assert original.decision == "ALLOW" and changed.decision == "ALLOW"
    assert original.permit_ref != changed.permit_ref
    assert original.clearance_ref != changed.clearance_ref
