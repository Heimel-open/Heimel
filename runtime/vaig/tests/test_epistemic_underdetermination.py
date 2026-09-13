import pytest

from vaig.epistemic_underdetermination import (
    AlternativeHypothesis,
    EpistemicState,
    EpistemicUnderdeterminationGate,
    UnderdeterminationInputError,
    UnderdeterminationKind,
)


def alt(
    alternative_id,
    claim,
    tests=(),
    consequences=(),
    viable=True,
):
    return AlternativeHypothesis(
        alternative_id=alternative_id,
        claim=claim,
        evidence_refs=("evidence/{}.json".format(alternative_id),),
        discriminating_tests=tuple(tests),
        consequences=tuple(consequences),
        viable=viable,
    )


def test_contrastive_state_preserves_alternatives_and_defers_divergent_consequence():
    result = EpistemicUnderdeterminationGate().assess(
        alternatives=(
            alt(
                "a",
                "A explains the observation.",
                tests=("Intervene on A while holding B constant.",),
                consequences=("execute-a",),
            ),
            alt(
                "b",
                "B explains the observation.",
                tests=("Intervene on B while holding A constant.",),
                consequences=("execute-b",),
            ),
        ),
        shared_evidence_refs=("evidence/shared.csv",),
        unconceived_alternative_risk=True,
    )

    assert result.epistemic_state == EpistemicState.UNDERDETERMINED
    assert result.kind == UnderdeterminationKind.CONTRASTIVE
    assert [item.alternative_id for item in result.surviving_alternatives] == ["a", "b"]
    assert result.requires_human_review is True
    assert result.execution_authority is False
    assert result.requires_reht_clearance is True


def test_holist_state_exposes_multiple_revision_targets():
    result = EpistemicUnderdeterminationGate().assess(
        alternatives=(alt("model", "The focal model remains viable."),),
        shared_evidence_refs=("evidence/failed-prediction.json",),
        failed_prediction=True,
        revision_targets=(
            "focal hypothesis",
            "instrument calibration",
            "environment assumption",
        ),
    )

    assert result.epistemic_state == EpistemicState.UNDERDETERMINED
    assert result.kind == UnderdeterminationKind.HOLIST
    assert len(result.revision_targets) == 3


def test_same_consequence_allows_only_common_bounded_action_path():
    result = EpistemicUnderdeterminationGate().assess(
        alternatives=(
            alt("a", "Explanation A", consequences=("observe",)),
            alt("b", "Explanation B", consequences=("observe",)),
        ),
        shared_evidence_refs=("evidence/shared.md",),
    )

    assert result.epistemic_state == EpistemicState.UNDERDETERMINED
    assert result.common_bounded_action_possible is True
    assert result.requires_human_review is False
    assert result.execution_authority is False


def test_single_viable_alternative_is_determined():
    result = EpistemicUnderdeterminationGate().assess(
        alternatives=(
            alt("survivor", "Supported"),
            alt("rejected", "Rejected", viable=False),
        ),
        shared_evidence_refs=("evidence/discriminator.md",),
    )

    assert result.epistemic_state == EpistemicState.DETERMINED
    assert result.kind == UnderdeterminationKind.NONE


def test_missing_shared_evidence_is_insufficient():
    result = EpistemicUnderdeterminationGate().assess(
        alternatives=(alt("a", "A"), alt("b", "B")),
        shared_evidence_refs=(),
    )

    assert result.epistemic_state == EpistemicState.INSUFFICIENT_EVIDENCE
    assert result.common_bounded_action_possible is False


def test_no_viable_alternative_is_insufficient():
    result = EpistemicUnderdeterminationGate().assess(
        alternatives=(
            alt("a", "Rejected A", viable=False),
            alt("b", "Rejected B", viable=False),
        ),
        shared_evidence_refs=("evidence/shared.md",),
    )

    assert result.epistemic_state == EpistemicState.INSUFFICIENT_EVIDENCE
    assert result.surviving_alternatives == ()
    assert result.common_bounded_action_possible is False
    assert result.rationale == ("No viable alternative was supplied.",)


def test_duplicate_alternative_ids_fail_closed():
    with pytest.raises(UnderdeterminationInputError, match="must be unique"):
        EpistemicUnderdeterminationGate().assess(
            alternatives=(alt("same", "First"), alt("same", "Second")),
            shared_evidence_refs=("evidence/shared.md",),
        )


def test_serialized_assessment_keeps_authority_boundary():
    result = EpistemicUnderdeterminationGate().assess(
        alternatives=(alt("a", "A"), alt("b", "B")),
        shared_evidence_refs=("evidence/shared.md",),
    ).to_dict()

    assert result["epistemic_state"] == "UNDERDETERMINED"
    assert result["execution_authority"] is False
    assert result["requires_reht_clearance"] is True
