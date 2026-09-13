from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from valo_kernel.contracts.verification_proof import (
    RegenerationOutcome,
    VerificationCheckStatus,
    VerificationMethod,
    VerificationProofOutcome,
    assess_regeneration,
    assess_verification_proof,
    seal_verification_check,
    seal_verification_proof,
    seal_verification_step_anchor,
)

NOW = datetime(2026, 8, 17, 16, 50, tzinfo=UTC)
DEFINITION = "d" * 64
INPUT = "a" * 64
MID = "b" * 64
OUTPUT = "c" * 64


def _reference_check():
    return seal_verification_check(
        check_id="check:reference",
        method=VerificationMethod.REFERENCE,
        status=VerificationCheckStatus.PASS,
        basis_refs=("reference:iapws",),
        evidence_refs=("evidence:reference-result",),
    )


def _cross_check():
    return seal_verification_check(
        check_id="check:independent-route",
        method=VerificationMethod.INDEPENDENT_ROUTE,
        status=VerificationCheckStatus.PASS,
        basis_refs=("route:analytic", "route:numeric"),
        evidence_refs=("evidence:route-agreement",),
    )


def _refusal_check(*, observed: bool = True):
    return seal_verification_check(
        check_id="check:expected-refusal",
        method=VerificationMethod.EXPECTED_REFUSAL,
        status=(
            VerificationCheckStatus.PASS
            if observed
            else VerificationCheckStatus.FAIL
        ),
        basis_refs=("invalid-case:outside-domain",),
        evidence_refs=("evidence:refusal",) if observed else (),
        reason_codes=() if observed else ("INVALID_CASE_ACCEPTED",),
        refusal_expected=True,
        refusal_observed=observed,
    )


def _proof(
    *,
    proof_id: str = "proof:1",
    created_at: datetime = NOW,
    refusal_observed: bool = True,
    ledger_suffix: str = "1",
    output_digest: str = OUTPUT,
):
    reference = _reference_check()
    cross = _cross_check()
    refusal = _refusal_check(observed=refusal_observed)
    first = seal_verification_step_anchor(
        step_id="step:1",
        subject_ref="calculation:1",
        definition_digest=DEFINITION,
        input_digest=INPUT,
        output_digest=MID,
        check_digests=(cross.check_digest, reference.check_digest),
        ledger_anchor_ref=f"ledger:first:{ledger_suffix}",
    )
    second = seal_verification_step_anchor(
        step_id="step:2",
        subject_ref="calculation:1",
        definition_digest=DEFINITION,
        input_digest=MID,
        output_digest=output_digest,
        check_digests=(refusal.check_digest,),
        ledger_anchor_ref=f"ledger:second:{ledger_suffix}",
        previous_step_digest=first.step_digest,
    )
    return seal_verification_proof(
        proof_id=proof_id,
        tenant_id="tenant:1",
        subject_ref="calculation:1",
        version_ref="capability:v1",
        definition_digest=DEFINITION,
        input_digest=INPUT,
        output_digest=output_digest,
        required_methods=(
            VerificationMethod.REFERENCE,
            VerificationMethod.INDEPENDENT_ROUTE,
            VerificationMethod.EXPECTED_REFUSAL,
        ),
        checks=(refusal, reference, cross),
        step_anchors=(first, second),
        created_at=created_at,
    )


def test_complete_proof_binds_independent_checks_and_creates_no_authority():
    proof = _proof()
    assessment = assess_verification_proof(proof)

    assert assessment.outcome == VerificationProofOutcome.COMPLETE
    assert assessment.can_rely_on_verification is True
    assert assessment.blocking_check_ids == ()
    assert assessment.missing_methods == ()
    assert proof.authority_effect == "NO_AUTHORITY_CREATION"
    assert proof.can_issue_clearance is False
    assert proof.can_execute is False
    assert assessment.can_issue_clearance is False
    assert assessment.can_execute is False


def test_reference_and_cross_route_passes_require_evidence():
    with pytest.raises(ValidationError, match="PASS verification check requires evidence"):
        seal_verification_check(
            check_id="check:no-evidence",
            method=VerificationMethod.REFERENCE,
            status=VerificationCheckStatus.PASS,
            basis_refs=("reference:known-value",),
        )


def test_expected_refusal_is_positive_only_when_invalid_case_is_refused():
    passed = _refusal_check(observed=True)
    failed = _refusal_check(observed=False)

    assert passed.status == VerificationCheckStatus.PASS
    assert failed.status == VerificationCheckStatus.FAIL

    with pytest.raises(
        ValidationError,
        match="EXPECTED_REFUSAL status must PASS only when refusal is observed",
    ):
        seal_verification_check(
            check_id="check:lying-refusal",
            method=VerificationMethod.EXPECTED_REFUSAL,
            status=VerificationCheckStatus.PASS,
            basis_refs=("invalid-case:1",),
            evidence_refs=("evidence:accepted",),
            refusal_expected=True,
            refusal_observed=False,
        )


def test_failed_required_refusal_control_makes_proof_incomplete():
    proof = _proof(refusal_observed=False)
    assessment = assess_verification_proof(proof)

    assert assessment.outcome == VerificationProofOutcome.INCOMPLETE
    assert assessment.can_rely_on_verification is False
    assert assessment.blocking_check_ids == ("check:expected-refusal",)
    assert assessment.missing_methods == (VerificationMethod.EXPECTED_REFUSAL,)
    assert set(assessment.reason_codes) == {
        "REQUIRED_CHECK_NOT_PASS",
        "REQUIRED_METHOD_MISSING",
    }


def test_missing_required_verification_method_fails_closed():
    reference = _reference_check()
    step = seal_verification_step_anchor(
        step_id="step:reference-only",
        subject_ref="calculation:1",
        definition_digest=DEFINITION,
        input_digest=INPUT,
        output_digest=OUTPUT,
        check_digests=(reference.check_digest,),
        ledger_anchor_ref="ledger:reference-only",
    )
    proof = seal_verification_proof(
        proof_id="proof:missing-method",
        tenant_id="tenant:1",
        subject_ref="calculation:1",
        version_ref="capability:v1",
        definition_digest=DEFINITION,
        input_digest=INPUT,
        output_digest=OUTPUT,
        required_methods=(
            VerificationMethod.REFERENCE,
            VerificationMethod.INDEPENDENT_ROUTE,
        ),
        checks=(reference,),
        step_anchors=(step,),
        created_at=NOW,
    )

    assessment = assess_verification_proof(proof)

    assert assessment.outcome == VerificationProofOutcome.INCOMPLETE
    assert assessment.missing_methods == (VerificationMethod.INDEPENDENT_ROUTE,)
    assert assessment.reason_codes == ("REQUIRED_METHOD_MISSING",)


def test_every_check_must_be_bound_to_a_step_anchor():
    reference = _reference_check()
    cross = _cross_check()
    step = seal_verification_step_anchor(
        step_id="step:partial",
        subject_ref="calculation:1",
        definition_digest=DEFINITION,
        input_digest=INPUT,
        output_digest=OUTPUT,
        check_digests=(reference.check_digest,),
        ledger_anchor_ref="ledger:partial",
    )

    with pytest.raises(
        ValidationError, match="every verification check must be anchored to a step"
    ):
        seal_verification_proof(
            proof_id="proof:partial",
            tenant_id="tenant:1",
            subject_ref="calculation:1",
            version_ref="capability:v1",
            definition_digest=DEFINITION,
            input_digest=INPUT,
            output_digest=OUTPUT,
            required_methods=(VerificationMethod.REFERENCE,),
            checks=(reference, cross),
            step_anchors=(step,),
            created_at=NOW,
        )


def test_step_chain_binds_definition_and_ordered_input_output():
    reference = _reference_check()
    cross = _cross_check()
    first = seal_verification_step_anchor(
        step_id="step:first",
        subject_ref="calculation:1",
        definition_digest=DEFINITION,
        input_digest=INPUT,
        output_digest=MID,
        check_digests=(reference.check_digest,),
        ledger_anchor_ref="ledger:first",
    )
    broken = seal_verification_step_anchor(
        step_id="step:broken",
        subject_ref="calculation:1",
        definition_digest=DEFINITION,
        input_digest="e" * 64,
        output_digest=OUTPUT,
        check_digests=(cross.check_digest,),
        ledger_anchor_ref="ledger:broken",
        previous_step_digest=first.step_digest,
    )

    with pytest.raises(
        ValidationError, match="verification step input/output chain mismatch"
    ):
        seal_verification_proof(
            proof_id="proof:broken-chain",
            tenant_id="tenant:1",
            subject_ref="calculation:1",
            version_ref="capability:v1",
            definition_digest=DEFINITION,
            input_digest=INPUT,
            output_digest=OUTPUT,
            required_methods=(
                VerificationMethod.REFERENCE,
                VerificationMethod.INDEPENDENT_ROUTE,
            ),
            checks=(reference, cross),
            step_anchors=(first, broken),
            created_at=NOW,
        )


def test_step_definition_mismatch_fails_closed():
    reference = _reference_check()
    step = seal_verification_step_anchor(
        step_id="step:wrong-definition",
        subject_ref="calculation:1",
        definition_digest="f" * 64,
        input_digest=INPUT,
        output_digest=OUTPUT,
        check_digests=(reference.check_digest,),
        ledger_anchor_ref="ledger:wrong-definition",
    )

    with pytest.raises(ValidationError, match="verification step definition mismatch"):
        seal_verification_proof(
            proof_id="proof:wrong-definition",
            tenant_id="tenant:1",
            subject_ref="calculation:1",
            version_ref="capability:v1",
            definition_digest=DEFINITION,
            input_digest=INPUT,
            output_digest=OUTPUT,
            required_methods=(VerificationMethod.REFERENCE,),
            checks=(reference,),
            step_anchors=(step,),
            created_at=NOW,
        )


def test_regeneration_matches_semantics_not_run_identity_or_ledger_location():
    first = _proof(proof_id="proof:first", ledger_suffix="a")
    second = _proof(
        proof_id="proof:second",
        created_at=NOW + timedelta(seconds=10),
        ledger_suffix="b",
    )

    assessment = assess_regeneration(first, second)

    assert first.proof_digest != second.proof_digest
    assert first.reproduction_digest == second.reproduction_digest
    assert assessment.outcome == RegenerationOutcome.MATCH
    assert assessment.matching_reproduction_digest is True


def test_regeneration_detects_output_change():
    first = _proof(proof_id="proof:first")
    second = _proof(proof_id="proof:second", output_digest="e" * 64)

    assessment = assess_regeneration(first, second)

    assert assessment.outcome == RegenerationOutcome.MISMATCH
    assert assessment.matching_reproduction_digest is False
    assert assessment.reason_codes == ("REPRODUCTION_DIGEST_MISMATCH",)


def test_check_digest_tampering_fails_closed():
    check = _reference_check()
    payload = check.model_dump(mode="python")
    payload["basis_refs"] = ("reference:tampered",)

    with pytest.raises(ValidationError, match="verification check digest mismatch"):
        type(check)(**payload)


def test_proof_digest_tampering_fails_closed():
    proof = _proof()
    payload = proof.model_dump(mode="python")
    payload["created_at"] = NOW + timedelta(days=1)

    with pytest.raises(ValidationError, match="verification proof digest mismatch"):
        type(proof)(**payload)
