from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from src.valo_platform.action_envelope.models import (
    ActionDecision,
    ActionType,
    ConsequenceClass,
    PurposeRecordRef,
)
from src.valo_platform.content_operations import (
    PublicationAction,
    PublicationActionCase,
    PublicationArtifact,
    PublicationPolicyEvaluator,
    PublicationPolicyProfile,
    PublicationPrivacy,
    PublicationRiskDomain,
    PublicationRiskEvidence,
    PublicationRollback,
)
from src.valo_platform.decision_governance.action_case import (
    ActionCaseLifecycleState,
    ActionCaseRecord,
)
from src.valo_platform.decision_governance.models import ActionCaseStatus


def sha(char: str) -> str:
    return "sha256:" + char * 64


def policy(now: datetime, **updates: object) -> PublicationPolicyProfile:
    payload: dict[str, object] = {
        "policy_id": "policy-publication-1",
        "version": "1",
        "tenant_id": "tenant-1",
        "established_by": "human:publisher",
        "authority_ref": "authority:board:1",
        "mandate_ref": "mandate:tenant-1:publisher:1",
        "mandate_fingerprint": sha("1"),
        "allowed_principal_ids": ("human:publisher",),
        "allowed_providers": ("youtube",),
        "allowed_account_refs": ("youtube-account:1",),
        "allowed_channel_refs": ("youtube-channel:1",),
        "allowed_languages": ("en", "no"),
        "allowed_jurisdictions": ("EU", "NO"),
        "auto_clear_low_risk": True,
        "allow_public_autoclear": False,
        "max_publications_24h": 4,
        "max_batch_size": 2,
        "max_spend": 25.0,
        "max_schedule_horizon_hours": 72,
        "required_approver_roles": ("responsible_publisher",),
        "effective_from": now - timedelta(hours=1),
        "effective_until": now + timedelta(days=1),
    }
    payload.update(updates)
    return PublicationPolicyProfile.model_validate(payload)


def action_case(profile: PublicationPolicyProfile) -> ActionCaseRecord:
    now = datetime.now(timezone.utc)
    return ActionCaseRecord(
        case_id="case-publication-1",
        tenant_id="tenant-1",
        environment="test",
        record_version=1,
        case_hash=sha("2"),
        decision_state=ActionCaseStatus.READY_FOR_REHT,
        lifecycle_state=ActionCaseLifecycleState.SUBMITTED,
        purpose_record_ref=PurposeRecordRef(
            purpose_id="purpose-content",
            version="1",
            record_ref="purpose:tenant-1:content:1",
            fingerprint=sha("3"),
            established_by="human:publisher",
            authority_ref="authority:board:1",
            evidence_refs=["evidence:source:1"],
        ),
        purpose_binding_ref="purpose-binding:content:1",
        mandate_ref=profile.mandate_ref,
        mandate_fingerprint=profile.mandate_fingerprint,
        evidence_refs=(
            "evidence:source:1",
            "evidence:claim:1",
            "evidence:rights:1",
        ),
        evidence_fingerprint=sha("4"),
        action_class=ActionType.EXTERNAL_PUBLICATION,
        consequence_class=ConsequenceClass.C2_MEDIUM,
        created_at=now,
        updated_at=now,
    )


def publication_case(
    profile: PublicationPolicyProfile,
    **updates: object,
) -> PublicationActionCase:
    payload: dict[str, object] = {
        "tenant_id": profile.tenant_id,
        "principal_id": "human:publisher",
        "delegated_mandate_ref": profile.mandate_ref,
        "provider": "youtube",
        "account_ref": "youtube-account:1",
        "channel_ref": "youtube-channel:1",
        "video": PublicationArtifact(
            artifact_ref="media:video:1",
            digest=sha("5"),
            media_type="video/mp4",
        ),
        "title": "Governed publication",
        "description": "Low-risk publication inside an explicit mandate.",
        "tags": ("governance",),
        "language": "en",
        "audiences": ("general",),
        "jurisdictions": ("NO",),
        "privacy_status": PublicationPrivacy.PRIVATE,
        "made_for_kids": False,
        "captions": (),
        "thumbnail": None,
        "source_refs": ("evidence:source:1",),
        "claim_evidence_refs": ("evidence:claim:1",),
        "rights_evidence_refs": ("evidence:rights:1",),
        "policy_refs": (f"{profile.policy_id}:{profile.version}",),
        "policy_snapshot_digest": profile.digest(),
        "rollback_capability": PublicationRollback.UNPUBLISH,
        "idempotency_key": "publication-1",
    }
    payload.update(updates)
    return PublicationActionCase(
        action_case=action_case(profile),
        publication=PublicationAction.model_validate(payload),
    )


def evaluate(
    profile: PublicationPolicyProfile,
    case: PublicationActionCase,
    risk: PublicationRiskEvidence | None = None,
    *,
    now: datetime,
):
    return PublicationPolicyEvaluator().evaluate(
        action_case=case,
        policy=profile,
        risk=risk or PublicationRiskEvidence(),
        now=now,
    )


def test_explicit_low_risk_mandate_allows_bounded_automatic_clearance() -> None:
    now = datetime.now(timezone.utc)
    profile = policy(now)
    case = publication_case(profile)

    result = evaluate(profile, case, now=now)

    assert result.decision is ActionDecision.ALLOW
    assert result.required_approver_roles == ()
    assert result.payload_digest == case.digest()
    assert result.policy_digest == profile.digest()


def test_policy_can_require_human_approval_for_every_publication() -> None:
    now = datetime.now(timezone.utc)
    profile = policy(now, auto_clear_low_risk=False)

    result = evaluate(profile, publication_case(profile), now=now)

    assert result.decision is ActionDecision.STEP_UP
    assert result.required_approver_roles == ("responsible_publisher",)


def test_public_visibility_requires_step_up_by_default() -> None:
    now = datetime.now(timezone.utc)
    profile = policy(now)
    case = publication_case(profile, privacy_status=PublicationPrivacy.PUBLIC)

    result = evaluate(profile, case, now=now)

    assert result.decision is ActionDecision.STEP_UP
    assert "public visibility" in result.reasons[0]


@pytest.mark.parametrize("domain", list(PublicationRiskDomain))
def test_high_risk_domains_require_step_up(domain: PublicationRiskDomain) -> None:
    now = datetime.now(timezone.utc)
    profile = policy(now)

    result = evaluate(
        profile,
        publication_case(profile),
        PublicationRiskEvidence(risk_domains=(domain,)),
        now=now,
    )

    assert result.decision is ActionDecision.STEP_UP
    assert domain.value in result.reasons[0]


def test_unsupported_claims_defer_for_more_evidence() -> None:
    now = datetime.now(timezone.utc)
    profile = policy(now)

    result = evaluate(
        profile,
        publication_case(profile),
        PublicationRiskEvidence(unsupported_claims=True),
        now=now,
    )

    assert result.decision is ActionDecision.DEFER
    assert "supporting evidence" in result.reasons[0]


@pytest.mark.parametrize(
    ("risk", "reason"),
    [
        (PublicationRiskEvidence(rights_ambiguity=True), "rights"),
        (PublicationRiskEvidence(semantic_uncertainty=True), "semantic"),
        (PublicationRiskEvidence(proposed_publications_24h=5), "frequency"),
        (PublicationRiskEvidence(batch_size=3), "batch"),
        (PublicationRiskEvidence(estimated_spend=25.01), "spend"),
    ],
)
def test_risk_and_aggregate_thresholds_require_step_up(
    risk: PublicationRiskEvidence,
    reason: str,
) -> None:
    now = datetime.now(timezone.utc)
    profile = policy(now)

    result = evaluate(profile, publication_case(profile), risk, now=now)

    assert result.decision is ActionDecision.STEP_UP
    assert reason in " ".join(result.reasons)


def test_scope_violation_denies_instead_of_escalating() -> None:
    now = datetime.now(timezone.utc)
    profile = policy(now)
    case = publication_case(profile, account_ref="youtube-account:other")

    result = evaluate(profile, case, now=now)

    assert result.decision is ActionDecision.DENY
    assert "account" in result.reasons[0]


def test_stale_policy_snapshot_defers_and_cannot_auto_clear() -> None:
    now = datetime.now(timezone.utc)
    profile = policy(now)
    case = publication_case(profile, policy_snapshot_digest=sha("f"))

    result = evaluate(profile, case, now=now)

    assert result.decision is ActionDecision.DEFER
    assert "stale" in result.reasons[0]


def test_expired_policy_defers() -> None:
    now = datetime.now(timezone.utc)
    profile = policy(
        now,
        effective_from=now - timedelta(days=2),
        effective_until=now - timedelta(days=1),
    )

    result = evaluate(profile, publication_case(profile), now=now)

    assert result.decision is ActionDecision.DEFER
    assert "effective window" in result.reasons[0]


def test_mandate_fingerprint_change_denies() -> None:
    now = datetime.now(timezone.utc)
    original = policy(now)
    changed_policy = policy(now, mandate_fingerprint=sha("e"))
    case = publication_case(original)

    result = evaluate(changed_policy, case, now=now)

    assert result.decision is ActionDecision.DENY
    assert "mandate fingerprint" in " ".join(result.reasons)


def test_past_schedule_defers_and_long_horizon_steps_up() -> None:
    now = datetime.now(timezone.utc)
    profile = policy(now)
    past = publication_case(profile, scheduled_for=now - timedelta(minutes=1))
    future = publication_case(profile, scheduled_for=now + timedelta(hours=73))

    assert evaluate(profile, past, now=now).decision is ActionDecision.DEFER
    assert evaluate(profile, future, now=now).decision is ActionDecision.STEP_UP


def test_policy_profile_is_strict_and_immutable() -> None:
    now = datetime.now(timezone.utc)
    payload = policy(now).model_dump(mode="python")
    payload["model_may_lower_thresholds"] = True

    with pytest.raises(ValidationError, match="Extra inputs"):
        PublicationPolicyProfile.model_validate(payload)


def test_policy_evaluator_has_no_clearance_or_execution_authority() -> None:
    evaluator = PublicationPolicyEvaluator()

    assert not hasattr(evaluator, "issue_clearance")
    assert not hasattr(evaluator, "create_commit_token")
    assert not hasattr(evaluator, "execute")
