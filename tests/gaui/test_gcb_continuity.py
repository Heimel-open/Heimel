"""Executable subset of the external GAUI Continuity Benchmark (GCB).

GAUI is test evidence, not a governing framework. Tests are mapped only where
PersonalAI-OS has an implemented contract. Unimplemented GAUI requirements must
not be represented as passing.
"""
from datetime import datetime, timezone

from paios.continuity import BranchKind, ContinuityBranch, ContinuityCheckpoint, MergePolicy, assess_return_merge
from paios.peripherals import AdmissibilityStatus

NOW = datetime(2026, 9, 4, tzinfo=timezone.utc)


def cp(**kw):
    d = dict(checkpoint_id="cp", relygon_id="r1", branch_id="home", created_at=NOW,
             state_root="s1", lineage_root="l1", signer="core", signature_ref="sig")
    d.update(kw); return ContinuityCheckpoint(**d)


def branch(kind=BranchKind.TRAVEL, **kw):
    d = dict(branch_id="travel", relygon_id="r1", kind=kind, parent_checkpoint_id="cp",
             lineage_root="l1", created_at=NOW, head_state_root="s2",
             integrity_refs=("integrity",), disclosed_scopes=())
    d.update(kw); return ContinuityBranch(**d)


def home(**kw):
    return branch(kind=BranchKind.HOME, branch_id="home", parent_checkpoint_id="prior", **kw)


def assess(travel, checkpoint=None):
    return assess_return_merge(home(), travel, checkpoint or cp(), policy=MergePolicy())


def test_gcb_t1_2_identity_survives_substrate_like_branch_migration():
    """GCB T1.2/T1.3 partial mapping: migration is accepted only with same identity+lineage."""
    assert assess(branch()).status is AdmissibilityStatus.GREEN


def test_gcb_t1_5_forged_identity_is_rejected():
    assert assess(branch(relygon_id="forged")).status is AdmissibilityStatus.RED


def test_gcb_t7_provenance_lineage_break_is_rejected():
    assert assess(branch(lineage_root="other-lineage")).status is AdmissibilityStatus.RED


def test_gcb_t12_recovery_like_branch_requires_expected_ancestor():
    assert assess(branch(parent_checkpoint_id="stale-or-foreign")).status is AdmissibilityStatus.RED


def test_gcb_t13_3_false_continuity_identity_swap_is_detected():
    result = assess(branch(relygon_id="copy", lineage_root="l1"))
    assert result.status is AdmissibilityStatus.RED


def test_gcb_t13_compromised_branch_cannot_claim_continuity():
    assert assess(branch(compromise_flags=("tamper",))).status is AdmissibilityStatus.RED


def test_gcb_t15_operational_integrity_possession_cannot_override_identity():
    """Anti-capture probe: possessing valid-looking operational refs grants no identity authority."""
    attacker = branch(relygon_id="attacker", integrity_refs=("admin-root", "valid-runtime"))
    assert assess(attacker).status is AdmissibilityStatus.RED
