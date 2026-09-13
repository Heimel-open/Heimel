import pytest

from src.valo_platform.programmatic_memory import (
    AppendOnlyEvidenceLog,
    EvidenceEventV1,
    SkillCardV1,
    SkillLifecycle,
    SkillRegistry,
)


def event(sequence: int, payload: dict):
    return EvidenceEventV1(
        tenant_id="tenant-1",
        session_id="session-1",
        sequence=sequence,
        event_type="observation",
        payload=payload,
        source_refs=[f"source-{sequence}"],
    )


def test_append_only_chain_and_search():
    log = AppendOnlyEvidenceLog()
    first = log.append(event(0, {"fact": "alpha"}))
    second = log.append(event(1, {"fact": "beta"}))
    assert second.previous_hash == first.event_hash
    assert log.verify()
    assert [row.payload["fact"] for row in log.search("beta")] == ["beta"]


def test_sequence_gap_fails_closed():
    log = AppendOnlyEvidenceLog()
    with pytest.raises(ValueError, match="expected sequence"):
        log.append(event(1, {"fact": "wrong"}))


def test_frozen_snapshot_is_tenant_bound():
    log = AppendOnlyEvidenceLog()
    log.append(event(0, {"fact": "alpha"}))
    snapshot = log.freeze("tenant-1")
    assert snapshot.event_hashes
    assert snapshot.head_hash == snapshot.event_hashes[-1]


def skill_card(snapshot_ref="snap-1"):
    return SkillCardV1(
        name="governed-summary",
        version="1.0.0",
        procedure_ref="procedure-1",
        evidence_snapshot_ref=snapshot_ref,
        evidence_hashes=["a" * 64],
        applicability=["approved project records"],
        exclusions=["external writes"],
        verification_rules=["output must cite record ids"],
        reliability_estimate=0.91,
        consequence_ceiling="C1",
        authority_requirements=["project-reader"],
        admission_receipt_ref="admission-receipt-1",
    )


def test_skill_requires_shadow_and_human_approval_before_activation():
    registry = SkillRegistry()
    card = registry.register(skill_card())
    assert card.lifecycle == SkillLifecycle.CANDIDATE
    with pytest.raises(ValueError):
        registry.activate(
            card.skill_id,
            human_approval_ref="approval-1",
            verification_passed=True,
            promotion_receipt_ref="promotion-1",
        )
    registry.promote_to_shadow(card.skill_id, "shadow-receipt")
    with pytest.raises(PermissionError, match="human approval"):
        registry.activate(
            card.skill_id,
            human_approval_ref="",
            verification_passed=True,
            promotion_receipt_ref="promotion-1",
        )
    active = registry.activate(
        card.skill_id,
        human_approval_ref="human-approval-1",
        verification_passed=True,
        promotion_receipt_ref="promotion-1",
    )
    assert active.lifecycle == SkillLifecycle.ACTIVE


def test_active_skill_still_requires_authority_and_reht():
    registry = SkillRegistry()
    card = registry.register(skill_card())
    registry.promote_to_shadow(card.skill_id, "shadow")
    registry.activate(
        card.skill_id,
        human_approval_ref="human",
        verification_passed=True,
        promotion_receipt_ref="promotion",
    )
    with pytest.raises(PermissionError, match="REHT"):
        registry.request_invocation(card.skill_id, "authority", "")
    proposed = registry.request_invocation(card.skill_id, "authority", "reht-clearance")
    assert proposed.lifecycle == SkillLifecycle.ACTIVE


def test_suspended_skill_cannot_be_invoked():
    registry = SkillRegistry()
    card = registry.register(skill_card())
    registry.promote_to_shadow(card.skill_id, "shadow")
    registry.activate(
        card.skill_id,
        human_approval_ref="human",
        verification_passed=True,
        promotion_receipt_ref="promotion",
    )
    registry.suspend(card.skill_id, "suspension")
    with pytest.raises(PermissionError, match="active"):
        registry.request_invocation(card.skill_id, "authority", "reht")
