from datetime import datetime, timezone

import pytest

from paios.continuity import (
    BranchKind,
    ContinuityBranch,
    ContinuityCheckpoint,
    ContinuityMergeError,
    MergePolicy,
    assess_return_merge,
    canonicalize_merge,
)
from paios.peripherals import AdmissibilityStatus, EvidenceEnvelope, EvidenceStage


NOW = datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc)


def evidence(observation_id: str, *, stage: EvidenceStage = EvidenceStage.VALIDATED, confidence: float = 0.9):
    return EvidenceEnvelope(
        observation_id=observation_id,
        stage=stage,
        confidence=confidence,
        provenance={"source": "test"},
        support_refs=("raw:1",),
    )


def checkpoint():
    return ContinuityCheckpoint(
        checkpoint_id="cp-1",
        relaion_id="r-1",
        branch_id="home-1",
        created_at=NOW,
        state_root="state-root-1",
        lineage_root="lineage-1",
        signer="core-1",
        signature_ref="sig-1",
    )


def home(*items: EvidenceEnvelope):
    return ContinuityBranch(
        branch_id="home-1",
        relaion_id="r-1",
        kind=BranchKind.HOME,
        parent_checkpoint_id="cp-0",
        lineage_root="lineage-1",
        created_at=NOW,
        head_state_root="home-root",
        evidence=tuple(items),
        integrity_refs=("home-integrity",),
    )


def travel(*items: EvidenceEnvelope, **overrides):
    data = dict(
        branch_id="travel-1",
        relaion_id="r-1",
        kind=BranchKind.TRAVEL,
        parent_checkpoint_id="cp-1",
        lineage_root="lineage-1",
        created_at=NOW,
        head_state_root="travel-root",
        evidence=tuple(items),
        mandate_ids=("travel-mandate",),
        integrity_refs=("travel-integrity",),
        compromise_flags=(),
        disclosed_scopes=("calendar",),
    )
    data.update(overrides)
    return ContinuityBranch(**data)


def policy(**overrides):
    data = dict(allowed_travel_scopes=frozenset({"calendar"}))
    data.update(overrides)
    return MergePolicy(**data)


def test_clean_return_is_green():
    result = assess_return_merge(home(evidence("h-1")), travel(evidence("t-1")), checkpoint(), policy=policy())
    assert result.status is AdmissibilityStatus.GREEN
    assert {e.observation_id for e in result.safe_evidence} == {"h-1", "t-1"}
    assert result.quarantined_evidence == ()


def test_wrong_parent_checkpoint_is_red():
    result = assess_return_merge(home(), travel(parent_checkpoint_id="other"), checkpoint(), policy=policy())
    assert result.status is AdmissibilityStatus.RED
    assert any("expected checkpoint" in reason for reason in result.reasons)


def test_wrong_relaion_identity_is_red():
    result = assess_return_merge(home(), travel(relaion_id="r-2"), checkpoint(), policy=policy())
    assert result.status is AdmissibilityStatus.RED
    assert any("identity mismatch" in reason for reason in result.reasons)


def test_compromise_indicator_is_red():
    result = assess_return_merge(home(), travel(compromise_flags=("device-rooted",)), checkpoint(), policy=policy())
    assert result.status is AdmissibilityStatus.RED
    assert any("compromise" in reason for reason in result.reasons)


def test_out_of_scope_disclosure_is_red():
    result = assess_return_merge(
        home(),
        travel(disclosed_scopes=("calendar", "medical")),
        checkpoint(),
        policy=policy(),
    )
    assert result.status is AdmissibilityStatus.RED
    assert any("outside allowed scope" in reason for reason in result.reasons)


def test_conflicting_same_stage_evidence_is_amber_and_both_sides_quarantined():
    left = evidence("obs-1", confidence=0.9)
    right = evidence("obs-1", confidence=0.4)
    result = assess_return_merge(home(left), travel(right), checkpoint(), policy=policy())
    assert result.status is AdmissibilityStatus.AMBER
    assert result.safe_evidence == ()
    assert len(result.quarantined_evidence) == 2
    assert any("conflicting evidence" in reason for reason in result.reasons)


def test_return_branch_cannot_import_canonical_evidence_directly():
    result = assess_return_merge(
        home(),
        travel(evidence("obs-1", stage=EvidenceStage.CANONICAL)),
        checkpoint(),
        policy=policy(),
    )
    assert result.status is AdmissibilityStatus.AMBER
    assert result.safe_evidence == ()
    assert len(result.quarantined_evidence) == 1


def test_policy_can_fail_closed_on_amber():
    left = evidence("obs-1", confidence=0.9)
    right = evidence("obs-1", confidence=0.4)
    result = assess_return_merge(
        home(left),
        travel(right),
        checkpoint(),
        policy=policy(allow_amber=False),
    )
    assert result.status is AdmissibilityStatus.RED


def test_red_merge_cannot_canonicalize():
    result = assess_return_merge(home(), travel(compromise_flags=("tamper",)), checkpoint(), policy=policy())
    with pytest.raises(ContinuityMergeError):
        canonicalize_merge(result)


def test_amber_canonicalize_returns_only_independently_safe_set():
    good = evidence("good")
    left = evidence("conflict", confidence=0.9)
    right = evidence("conflict", confidence=0.3)
    result = assess_return_merge(home(left), travel(good, right), checkpoint(), policy=policy())
    safe = canonicalize_merge(result)
    assert result.status is AdmissibilityStatus.AMBER
    assert {e.observation_id for e in safe} == {"good"}
