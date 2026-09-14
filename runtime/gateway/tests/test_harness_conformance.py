import pytest

from valo_gateway.harness_conformance import (
    HarnessAdmissionEvidence,
    HarnessConformanceError,
    HarnessDescriptor,
    HarnessState,
    require_harness_admission,
    verify_harness_admission,
)


def harness(name: str, *, state: HarnessState = HarnessState.KNOWN):
    return HarnessDescriptor(
        harness_id=name,
        version="v1",
        config_digest="sha256:" + "a" * 64,
        provenance_ref=f"prov:{name}",
        state=state,
    )


def evidence(**overrides):
    values = dict(
        incoming_harness=harness("incoming"),
        external_harness=harness("external"),
        pre_induction_assessed=True,
        controlled_regrounding_applied=True,
        residual_induction_measured=True,
        residual_induction_within_bound=True,
        equivalence_scope="bounded-task-profile-v1",
        evidence_ref="veritas:harness-admission-1",
    )
    values.update(overrides)
    return HarnessAdmissionEvidence(**values)


def test_known_harness_transition_with_bounded_residual_is_admissible():
    result = verify_harness_admission(evidence())
    assert result.admissible_for_consequence_bearing_work is True
    assert result.reasons == ()


def test_external_harness_does_not_override_unknown_incoming_harness():
    result = verify_harness_admission(
        evidence(incoming_harness=harness("opaque", state=HarnessState.UNKNOWN))
    )
    assert result.admissible_for_consequence_bearing_work is False
    assert "incoming_harness_unknown" in result.reasons


def test_pre_induced_worker_requires_assessment_and_regrounding():
    result = verify_harness_admission(
        evidence(pre_induction_assessed=False, controlled_regrounding_applied=False)
    )
    assert result.admissible_for_consequence_bearing_work is False
    assert "pre_induction_not_assessed" in result.reasons
    assert "controlled_regrounding_not_applied" in result.reasons


def test_residual_induction_out_of_bound_fails_closed():
    with pytest.raises(HarnessConformanceError, match="residual_induction_out_of_bound"):
        require_harness_admission(evidence(residual_induction_within_bound=False))


def test_unmeasured_residual_never_promotes_to_consequence_bearing_work():
    result = verify_harness_admission(
        evidence(residual_induction_measured=False, residual_induction_within_bound=False)
    )
    assert result.admissible_for_consequence_bearing_work is False
    assert "residual_induction_not_measured" in result.reasons
