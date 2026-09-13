from __future__ import annotations

from datetime import timedelta

import pytest
from pydantic import ValidationError

from valo_kernel.contracts import (
    CapabilityProviderBinding,
    EntityType,
    ExternalIdentityBridge,
    ProviderLossScenario,
    RecoveryAnchor,
    RecoveryPlan,
    SovereignArtifact,
    SovereignArtifactKind,
    SovereigntyOutcome,
    canonical_digest,
)
from valo_kernel.kernel import (
    FailClosedError,
    assess_disclosure,
    assess_provider_loss,
    seal_disclosure_authorization,
    seal_sovereign_domain_manifest,
)

from .conftest import entity_event
from .test_workspace import _register_purpose, _workspace


def _artifacts(*, provider_bound_kind: SovereignArtifactKind | None = None):
    result = []
    for index, kind in enumerate(SovereignArtifactKind, start=1):
        provider_bound = kind is provider_bound_kind
        result.append(
            SovereignArtifact(
                artifact_id=f"artifact-{index}",
                kind=kind,
                artifact_digest=f"{index:x}" * 64,
                format_id=f"valo.{kind.value.lower()}.v1",
                principal_controlled_copy=not provider_bound,
                custodian_ids=("provider-a",) if provider_bound else (),
            )
        )
    return tuple(result)


def _recovery_plan(*, provider_bound: bool = False) -> RecoveryPlan:
    anchors = (
        RecoveryAnchor(
            anchor_id="anchor-principal",
            independence_domain="physical-backup",
            principal_controlled=True,
        ),
        RecoveryAnchor(
            anchor_id="anchor-provider-a",
            independence_domain="custodian-a",
            provider_id="provider-a",
            principal_controlled=False,
        ),
    )
    return RecoveryPlan(
        recovery_method="threshold",
        threshold=2 if provider_bound else 1,
        anchors=anchors,
    )


def _providers():
    return (
        CapabilityProviderBinding(
            provider_id="provider-a",
            capability_classes=("reasoning", "payments"),
        ),
        CapabilityProviderBinding(
            provider_id="provider-b",
            capability_classes=("reasoning", "camera"),
        ),
    )


def _manifest(*, provider_bound_kind=None, provider_bound_recovery=False):
    return seal_sovereign_domain_manifest(
        manifest_id="manifest-1",
        tenant_id="tenant-a",
        principal_id="principal-1",
        source_state_root="a" * 64,
        event_chain_head_digest="b" * 64,
        artifacts=_artifacts(provider_bound_kind=provider_bound_kind),
        recovery_plan=_recovery_plan(provider_bound=provider_bound_recovery),
        providers=_providers(),
    )


def test_manifest_requires_every_sovereign_artifact_class() -> None:
    with pytest.raises(ValidationError, match="missing required artifacts"):
        seal_sovereign_domain_manifest(
            manifest_id="manifest-1",
            tenant_id="tenant-a",
            principal_id="principal-1",
            source_state_root="a" * 64,
            event_chain_head_digest="b" * 64,
            artifacts=_artifacts()[:-1],
            recovery_plan=_recovery_plan(),
            providers=_providers(),
        )


def test_provider_loss_can_degrade_capability_without_breaking_sovereignty() -> None:
    manifest = _manifest()
    assessment = assess_provider_loss(
        manifest,
        ProviderLossScenario(
            scenario_id="lose-provider-b",
            lost_provider_ids=("provider-b",),
        ),
    )

    assert assessment.outcome is SovereigntyOutcome.PASS
    assert assessment.violations == ()
    assert assessment.degraded_capability_classes == ("camera",)
    assert assessment.capability_degradation_allowed is True


def test_provider_loss_fails_when_required_state_copy_disappears() -> None:
    manifest = _manifest(provider_bound_kind=SovereignArtifactKind.IDENTITY)
    assessment = assess_provider_loss(
        manifest,
        ProviderLossScenario(
            scenario_id="lose-provider-a",
            lost_provider_ids=("provider-a",),
        ),
    )

    assert assessment.outcome is SovereigntyOutcome.DENY
    assert any(
        item.code == "RECONSTRUCTION_ARTIFACT_UNAVAILABLE"
        for item in assessment.violations
    )


def test_provider_loss_fails_when_recovery_threshold_is_lost() -> None:
    manifest = _manifest(provider_bound_recovery=True)
    assessment = assess_provider_loss(
        manifest,
        ProviderLossScenario(
            scenario_id="lose-provider-a",
            lost_provider_ids=("provider-a",),
        ),
    )

    assert assessment.outcome is SovereigntyOutcome.DENY
    assert any(
        item.code == "RECOVERY_THRESHOLD_UNAVAILABLE"
        for item in assessment.violations
    )


def test_provider_state_cannot_be_authoritative_or_issue_clearance() -> None:
    with pytest.raises(ValidationError):
        CapabilityProviderBinding(
            provider_id="provider-a",
            capability_classes=("reasoning",),
            state_role="AUTHORITATIVE",
        )
    with pytest.raises(ValidationError):
        CapabilityProviderBinding(
            provider_id="provider-a",
            capability_classes=("reasoning",),
            can_issue_clearance=True,
        )


def test_legacy_identity_bridge_is_mapping_not_root_identity() -> None:
    bridge = ExternalIdentityBridge(
        bridge_id="bridge-bank-a",
        principal_id="principal-1",
        external_system_id="bank-a",
        external_subject_ref="customer:123",
        external_subject_digest="c" * 64,
    )
    assert bridge.mapping_only is True
    assert bridge.external_identifier_is_not_root_identity is True
    assert bridge.can_issue_clearance is False


def _governed_workspace(engine):
    engine.append(
        entity_event(
            "tenant-a",
            "job-1",
            entity_type=EntityType.JOB,
            state="READY",
        )
    )
    _register_purpose(engine)
    moment = __import__("valo_kernel").utcnow()
    return _workspace(engine, moment=moment), moment


def _authorization(workspace, *, moment, **updates):
    projection = workspace.projection
    values = {
        "authorization_id": "disclose-1",
        "tenant_id": workspace.spec.tenant_id,
        "principal_id": "principal-1",
        "destination_id": "provider-a",
        "purpose_id": workspace.spec.purpose_id,
        "projection_id": projection.projection_id,
        "projection_digest": canonical_digest(projection.model_dump(mode="json")),
        "source_state_root": projection.source_state_root,
        "source_event_position": projection.source_event_position,
        "allowed_object_refs": tuple(sorted(item.ref for item in projection.objects)),
        "authority_basis_refs": ("delegation:disclosure-1",),
        "authority_state_digest": "d" * 64,
        "issued_at": moment - timedelta(seconds=1),
        "valid_until": moment + timedelta(minutes=5),
    }
    values.update(updates)
    return seal_disclosure_authorization(**values)


def test_disclosure_passes_only_for_exact_destination_projection_and_fresh_state(engine) -> None:
    workspace, moment = _governed_workspace(engine)
    authorization = _authorization(workspace, moment=moment)

    assessment = assess_disclosure(
        workspace,
        authorization,
        destination_id="provider-a",
        current_state_root=workspace.projection.source_state_root,
        current_authority_state_digest="d" * 64,
        moment=moment,
    )

    assert assessment.outcome.value == "PASS"
    assert assessment.creates_disclosure is False
    assert assessment.can_issue_clearance is False


@pytest.mark.parametrize(
    ("kwargs", "code"),
    (
        ({"destination_id": "provider-b"}, "DESTINATION_BINDING"),
        ({"current_state_root": "e" * 64}, "STALE_STATE"),
        ({"current_authority_state_digest": "f" * 64}, "STALE_AUTHORITY"),
        ({"revoked_authority_basis_refs": ("delegation:disclosure-1",)}, "AUTHORITY_REVOKED"),
    ),
)
def test_disclosure_fails_closed_on_binding_or_freshness_change(engine, kwargs, code) -> None:
    workspace, moment = _governed_workspace(engine)
    authorization = _authorization(workspace, moment=moment)
    values = {
        "destination_id": "provider-a",
        "current_state_root": workspace.projection.source_state_root,
        "current_authority_state_digest": "d" * 64,
        "moment": moment,
    }
    values.update(kwargs)

    assessment = assess_disclosure(workspace, authorization, **values)

    assert assessment.outcome.value == "DENY"
    assert code in {item.code for item in assessment.mismatches}


def test_disclosure_tamper_is_hard_failure(engine) -> None:
    workspace, moment = _governed_workspace(engine)
    authorization = _authorization(workspace, moment=moment)
    tampered = authorization.model_copy(update={"destination_id": "provider-b"})

    with pytest.raises(FailClosedError, match="unsealed or tampered"):
        assess_disclosure(
            workspace,
            tampered,
            destination_id="provider-b",
            current_state_root=workspace.projection.source_state_root,
            current_authority_state_digest="d" * 64,
            moment=moment,
        )
