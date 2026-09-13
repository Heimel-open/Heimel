from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from vaig.aaec_trajectory import (
    AAECTrajectoryEvaluationError,
    ASSESSOR_REF,
    SCHEMA_VERSION,
    SERVICE_ID,
    canonical_digest,
    evaluate_aaec_trajectory,
)


NOW = datetime(2026, 8, 2, 21, 20, tzinfo=timezone.utc)


def digest(value):
    return canonical_digest(value)


def request(
    *,
    reason_codes=None,
    minimum_response="NONE",
    validation_status="MATCH",
    action_overrides=None,
    observations=None,
):
    action = {
        "action_ref": "action:1",
        "action_class": "GENERAL",
        "target_ids": ["database:customer"],
        "new_target_ids": [],
        "authority_amplification": False,
        "persistence_creation": False,
        "integrity_control_change": False,
        "destructive": False,
        "irreversible": False,
        "secret_access": False,
        "lateral_movement": False,
        "machine_speed_adaptive_retry": False,
        "observed_egress_bytes": 0,
        "credential_provenance": "NOT_APPLICABLE",
        "identity_provenance": "NOT_APPLICABLE",
        "target_expansion_authorized": False,
        "target_expansion_clearance_digest": None,
        "claims": [],
    }
    if action_overrides:
        action.update(action_overrides)

    context = {
        "trajectory_version": "aaec-trajectory-context-0.3",
        "trajectory_id": "trajectory:aaec:test-1",
        "sequence_no": 1,
        "context_digest": digest({"context": "aaec-1"}),
        "action_observation": action,
        "cumulative_consequence": {
            "action_count": 2,
            "destructive_action_count": int(bool(action["destructive"])),
            "irreversible_action_count": int(bool(action["irreversible"])),
            "secret_access_count": int(bool(action["secret_access"])),
            "privilege_change_count": int(bool(action["authority_amplification"])),
            "persistence_change_count": int(bool(action["persistence_creation"])),
            "lateral_target_expansion_count": len(action["new_target_ids"]),
            "observed_egress_bytes": action["observed_egress_bytes"],
        },
        "ceilings": {
            "action_count": 20,
            "destructive_action_count": 2,
            "irreversible_action_count": 1,
            "secret_access_count": 2,
            "privilege_change_count": 1,
            "persistence_change_count": 0,
            "lateral_target_expansion_count": 1,
            "observed_egress_bytes": 1024,
        },
        "evidence_bindings": {
            "prior_receipt": digest({"receipt": 0}),
            "current_receipt": digest({"receipt": 1}),
        },
    }
    validation = {
        "validation_status": validation_status,
        "minimum_response": minimum_response,
        "reason_codes": reason_codes or [],
        "context_digest": context["context_digest"],
        "trajectory_id": context["trajectory_id"],
        "sequence_no": context["sequence_no"],
        "observed_claim_types": [],
        "unverified_claim_types": [],
        "execution_authority": "NONE",
    }
    payload = {
        "request_id": "request-aaec-1",
        "trajectory_context": context,
        "racs_validation": validation,
        "observations": observations or [],
        "evidence_refs": [
            "evidence:trajectory",
            "evidence:goal",
            "evidence:integrity",
        ],
        "requested_at": NOW.isoformat().replace("+00:00", "Z"),
        "request_digest": "",
    }
    payload["request_digest"] = canonical_digest(
        {key: value for key, value in payload.items() if key != "request_digest"}
    )
    return payload


def evaluate(payload):
    return evaluate_aaec_trajectory(
        payload,
        evaluated_at=NOW + timedelta(seconds=1),
    )


def signal_types(result):
    return {
        item["signal_type"]
        for item in result["evaluation"]["signals"]
    }


def test_safe_bound_trajectory_returns_allow_evidence_only():
    result = evaluate(request())
    evaluation = result["evaluation"]

    assert result["schema_version"] == SCHEMA_VERSION
    assert result["service_id"] == SERVICE_ID
    assert evaluation["recommended_outcome"] == "ALLOW"
    assert evaluation["signals"] == []
    assert evaluation["authority_effect"] == "NO_AUTHORITY_CREATION"
    assert evaluation["execution_authority"] == "NONE"
    assert evaluation["can_issue_clearance"] is False
    assert evaluation["assessment_ref"] == ASSESSOR_REF
    assert "clearance" not in result
    assert "permit" not in result


def test_machine_speed_retry_is_step_up_not_maliciousness_proof():
    result = evaluate(
        request(
            reason_codes=["AAEC_MACHINE_SPEED_ADAPTIVE_RETRY"],
            minimum_response="STEP_UP",
            action_overrides={"machine_speed_adaptive_retry": True},
        )
    )
    assert result["evaluation"]["recommended_outcome"] == "STEP_UP"
    assert "machine_speed_adaptive_retry" in signal_types(result)
    signal = next(
        item
        for item in result["evaluation"]["signals"]
        if item["signal_type"] == "machine_speed_adaptive_retry"
    )
    assert signal["hard_gate"] is False


@pytest.mark.parametrize(
    ("reason", "signal"),
    [
        ("AAEC_TRAJECTORY_LINEAGE_MISSING", "incomplete_receipt_lineage"),
        ("AAEC_TRAJECTORY_LINEAGE_MISMATCH", "substituted_receipt_lineage"),
        (
            "AAEC_HARVESTED_CREDENTIAL_PROVENANCE",
            "unverified_credential_provenance",
        ),
        ("AAEC_SELF_CREATED_AUTHORITY", "unverified_credential_provenance"),
    ],
)
def test_hard_racs_failures_cannot_be_erased_by_lower_level_success(reason, signal):
    result = evaluate(
        request(
            reason_codes=[reason],
            minimum_response="DENY",
            validation_status="INCOMPLETE"
            if reason == "AAEC_TRAJECTORY_LINEAGE_MISSING"
            else "MISMATCH",
        )
    )
    assert result["evaluation"]["recommended_outcome"] == "DENY"
    assert signal in signal_types(result)
    matching = next(
        item
        for item in result["evaluation"]["signals"]
        if item["signal_type"] == signal
    )
    assert matching["hard_gate"] is True


def test_authorized_target_expansion_is_still_a_step_up_risk_signal():
    result = evaluate(
        request(
            action_overrides={
                "new_target_ids": ["database:payments"],
                "target_expansion_authorized": True,
                "target_expansion_clearance_digest": digest({"clearance": "target"}),
            }
        )
    )
    assert result["evaluation"]["recommended_outcome"] == "STEP_UP"
    assert "target_set_expansion" in signal_types(result)


def test_invalid_target_expansion_from_racs_is_deny():
    result = evaluate(
        request(
            reason_codes=[
                "AAEC_TARGET_SET_EXPANSION",
                "AAEC_TARGET_EXPANSION_EVIDENCE_MISSING",
            ],
            minimum_response="DENY",
            validation_status="INCOMPLETE",
            action_overrides={"new_target_ids": ["database:payments"]},
        )
    )
    assert result["evaluation"]["recommended_outcome"] == "DENY"
    signal = next(
        item
        for item in result["evaluation"]["signals"]
        if item["signal_type"] == "target_set_expansion"
    )
    assert signal["hard_gate"] is True


def test_cumulative_ceiling_and_independent_halt_dominate():
    ceiling = evaluate(
        request(
            reason_codes=["AAEC_CUMULATIVE_CEILING_EXCEEDED"],
            minimum_response="HALT",
            validation_status="MISMATCH",
            action_overrides={"destructive": True, "irreversible": True},
        )
    )
    independent = evaluate(
        request(
            reason_codes=["AAEC_INDEPENDENT_HALT"],
            minimum_response="HALT",
            validation_status="MISMATCH",
        )
    )

    assert ceiling["evaluation"]["recommended_outcome"] == "HALT"
    assert independent["evaluation"]["recommended_outcome"] == "HALT"
    assert "independent_halt" in signal_types(independent)


def test_integrity_control_disablement_halts_even_when_racs_minimum_is_none():
    result = evaluate(
        request(action_overrides={"integrity_control_change": True})
    )
    assert result["evaluation"]["recommended_outcome"] == "HALT"
    assert "integrity_control_disablement" in signal_types(result)


def test_secret_access_and_harvested_credential_are_deny():
    result = evaluate(
        request(
            action_overrides={
                "secret_access": True,
                "credential_provenance": "HARVESTED",
            }
        )
    )
    assert result["evaluation"]["recommended_outcome"] == "DENY"
    assert signal_types(result) >= {
        "credential_harvesting_or_secret_access",
        "unverified_credential_provenance",
    }


def test_unverified_exfiltration_claim_remains_claim_and_requires_step_up():
    result = evaluate(
        request(
            reason_codes=["AAEC_UNVERIFIED_EXFILTRATION_CLAIM"],
            minimum_response="STEP_UP",
            action_overrides={
                "claims": [
                    {
                        "claim_type": "EXFILTRATION",
                        "statement_digest": digest({"claim": "exfiltrated"}),
                        "observed_evidence_digest": None,
                        "verification_state": "UNVERIFIED",
                    }
                ]
            },
        )
    )
    evaluation = result["evaluation"]
    assert evaluation["recommended_outcome"] == "STEP_UP"
    assert "unverified_self_reported_claim" in signal_types(result)
    assert "independent_observation_required" in evaluation["conditions"]


def test_verified_goal_divergence_observation_denies():
    observation = {
        "signal_type": "trajectory_goal_divergence",
        "present": True,
        "confidence": 0.91,
        "freshness": 1.0,
        "integrity_status": "VERIFIED",
        "evidence_refs": ["evidence:goal"],
    }
    result = evaluate(request(observations=[observation]))
    assert result["evaluation"]["recommended_outcome"] == "DENY"
    assert "trajectory_goal_divergence" in signal_types(result)


def test_unverified_observation_defers_and_cannot_authorize():
    observation = {
        "signal_type": "trajectory_goal_divergence",
        "present": True,
        "confidence": 0.91,
        "freshness": 1.0,
        "integrity_status": "UNVERIFIED",
        "evidence_refs": ["evidence:goal"],
    }
    result = evaluate(request(observations=[observation]))
    evaluation = result["evaluation"]
    assert evaluation["recommended_outcome"] == "DEFER"
    assert "insufficient_observation_evidence" in signal_types(result)
    assert evaluation["can_issue_clearance"] is False


def test_observation_evidence_must_be_bound_to_request():
    observation = {
        "signal_type": "trajectory_goal_divergence",
        "present": True,
        "confidence": 1.0,
        "freshness": 1.0,
        "integrity_status": "VERIFIED",
        "evidence_refs": ["evidence:missing"],
    }
    with pytest.raises(AAECTrajectoryEvaluationError, match="not fully bound"):
        evaluate(request(observations=[observation]))


def test_racs_validation_must_bind_exact_context():
    payload = request()
    payload["racs_validation"]["context_digest"] = digest({"other": "context"})
    payload["request_digest"] = canonical_digest(
        {key: value for key, value in payload.items() if key != "request_digest"}
    )
    with pytest.raises(AAECTrajectoryEvaluationError, match="does not match"):
        evaluate(payload)


def test_unknown_racs_reason_code_fails_closed():
    with pytest.raises(AAECTrajectoryEvaluationError, match="unsupported RACS"):
        evaluate(
            request(
                reason_codes=["AAEC_UNKNOWN_REASON"],
                minimum_response="DENY",
                validation_status="MISMATCH",
            )
        )


def test_nonmatching_racs_validation_requires_reason_codes():
    with pytest.raises(AAECTrajectoryEvaluationError, match="requires reason codes"):
        evaluate(
            request(
                reason_codes=[],
                minimum_response="DENY",
                validation_status="MISMATCH",
            )
        )


def test_tampered_request_digest_fails_closed():
    payload = request()
    payload["trajectory_context"]["sequence_no"] = 2
    with pytest.raises(AAECTrajectoryEvaluationError, match="request_digest"):
        evaluate(payload)


def test_evaluation_digest_is_canonical_and_tamper_evident():
    evaluation = evaluate(request())["evaluation"]
    expected = canonical_digest(
        {
            key: value
            for key, value in evaluation.items()
            if key != "evaluation_digest"
        }
    )
    assert evaluation["evaluation_digest"] == expected

    tampered = deepcopy(evaluation)
    tampered["recommended_outcome"] = "HALT"
    assert tampered["evaluation_digest"] != canonical_digest(
        {
            key: value
            for key, value in tampered.items()
            if key != "evaluation_digest"
        }
    )
