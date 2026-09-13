from valo_kernel import contracts

RACS_OUTCOMES = {"ALLOW", "MODIFY", "DEFER", "DENY", "STEP_UP", "HALT"}


def _decision(outcome: contracts.AdmissionOutcome) -> contracts.AdmissionDecision:
    return contracts.AdmissionDecision(
        decision_id=f"decision-{outcome.value.lower()}",
        tenant_id="tenant-a",
        candidate_id="candidate-1",
        evidence_id="evidence-1",
        candidate_digest="a" * 64,
        policy_id="policy-1",
        policy_digest="b" * 64,
        outcome=outcome,
        reason_codes=(f"TEST_{outcome.value}",),
        decided_at=contracts.utcnow(),
        can_enter_operational_state=outcome == contracts.AdmissionOutcome.ADMIT,
    )


def test_epistemic_outcomes_are_disjoint_from_racs_outcomes() -> None:
    assert {item.value for item in contracts.AdmissionOutcome}.isdisjoint(RACS_OUTCOMES)


def test_admission_decision_never_emits_execution_decision() -> None:
    for outcome in contracts.AdmissionOutcome:
        decision = _decision(outcome)

        assert decision.racs_outcome is None
        assert decision.can_authorize_execution is False
        assert decision.can_issue_clearance is False
        assert decision.can_create_authority is False
        assert "racs_outcome" not in decision.model_dump()
        assert "can_authorize_execution" not in decision.model_dump()


def test_hold_is_non_commitment_not_denial_or_defer() -> None:
    decision = _decision(contracts.AdmissionOutcome.HOLD)

    assert decision.is_epistemic_non_commitment is True
    assert decision.outcome.value == "HOLD"
    assert decision.outcome.value not in {"DENY", "DEFER"}


def test_admit_only_admits_premise_and_still_does_not_authorize_execution() -> None:
    decision = _decision(contracts.AdmissionOutcome.ADMIT)

    assert decision.can_enter_operational_state is True
    assert decision.is_epistemic_non_commitment is False
    assert decision.can_authorize_execution is False
    assert decision.racs_outcome is None
