from __future__ import annotations

from datetime import datetime

from ..contracts.common import canonical_digest, utcnow
from ..contracts.sovereignty import (
    DisclosureAssessment,
    DisclosureAuthorization,
    DisclosureMismatch,
    DisclosureOutcome,
    ProviderLossScenario,
    SovereignDomainManifest,
    SovereigntyAssessment,
    SovereigntyOutcome,
    SovereigntyViolation,
)
from ..contracts.workspace import GovernedWorkspaceEnvelope
from .errors import FailClosedError


def seal_sovereign_domain_manifest(**values: object) -> SovereignDomainManifest:
    provisional = SovereignDomainManifest(**values)
    return provisional.model_copy(update={"manifest_digest": provisional.computed_digest})


def seal_disclosure_authorization(**values: object) -> DisclosureAuthorization:
    provisional = DisclosureAuthorization(**values)
    return provisional.model_copy(
        update={"authorization_digest": provisional.computed_digest}
    )


def assess_provider_loss(
    manifest: SovereignDomainManifest,
    scenario: ProviderLossScenario,
    *,
    assessed_at: datetime | None = None,
) -> SovereigntyAssessment:
    if manifest.manifest_digest != manifest.computed_digest:
        raise FailClosedError("sovereign domain manifest is unsealed or tampered")

    provider_ids = {item.provider_id for item in manifest.providers}
    lost = set(scenario.lost_provider_ids)
    violations: list[SovereigntyViolation] = []

    unknown = sorted(lost - provider_ids)
    for provider_id in unknown:
        violations.append(
            SovereigntyViolation(
                code="UNKNOWN_PROVIDER",
                detail=f"provider-loss scenario references unknown provider: {provider_id}",
            )
        )

    for artifact in manifest.artifacts:
        surviving_custodians = set(artifact.custodian_ids) - lost
        if not artifact.principal_controlled_copy and not surviving_custodians:
            violations.append(
                SovereigntyViolation(
                    code="RECONSTRUCTION_ARTIFACT_UNAVAILABLE",
                    detail=(
                        "provider loss removes every available copy of required "
                        f"{artifact.kind.value} artifact"
                    ),
                    artifact_id=artifact.artifact_id,
                )
            )

    surviving_recovery_domains = {
        anchor.independence_domain
        for anchor in manifest.recovery_plan.anchors
        if anchor.principal_controlled or anchor.provider_id not in lost
    }
    if len(surviving_recovery_domains) < manifest.recovery_plan.threshold:
        violations.append(
            SovereigntyViolation(
                code="RECOVERY_THRESHOLD_UNAVAILABLE",
                detail=(
                    "provider loss leaves fewer independent recovery domains than "
                    "the configured recovery threshold"
                ),
            )
        )

    all_capability_classes = {
        capability
        for provider in manifest.providers
        for capability in provider.capability_classes
    }
    surviving_capability_classes = {
        capability
        for provider in manifest.providers
        if provider.provider_id not in lost
        for capability in provider.capability_classes
    }
    degraded_capability_classes = tuple(
        sorted(all_capability_classes - surviving_capability_classes)
    )

    outcome = SovereigntyOutcome.DENY if violations else SovereigntyOutcome.PASS
    moment = assessed_at or utcnow()
    provisional = SovereigntyAssessment(
        assessment_id=f"sovereignty:{scenario.scenario_id}",
        manifest_digest=manifest.manifest_digest,
        scenario_id=scenario.scenario_id,
        lost_provider_ids=scenario.lost_provider_ids,
        outcome=outcome,
        violations=tuple(violations),
        degraded_capability_classes=degraded_capability_classes,
        assessed_at=moment,
    )
    return provisional.model_copy(
        update={"assessment_digest": provisional.computed_digest}
    )


def assess_disclosure(
    workspace: GovernedWorkspaceEnvelope,
    authorization: DisclosureAuthorization,
    *,
    destination_id: str,
    current_state_root: str,
    current_authority_state_digest: str,
    revoked_authority_basis_refs: tuple[str, ...] = (),
    moment: datetime | None = None,
) -> DisclosureAssessment:
    if workspace.workspace_digest != workspace.computed_digest:
        raise FailClosedError("governed workspace is unsealed or tampered")
    if authorization.authorization_digest != authorization.computed_digest:
        raise FailClosedError("disclosure authorization is unsealed or tampered")

    evaluated_at = moment or utcnow()
    projection = workspace.projection
    projection_digest = canonical_digest(projection.model_dump(mode="json"))
    mismatches: list[DisclosureMismatch] = []

    def mismatch(code: str, detail: str) -> None:
        mismatches.append(DisclosureMismatch(code=code, detail=detail))

    if destination_id != authorization.destination_id:
        mismatch("DESTINATION_BINDING", "disclosure destination does not match authorization")
    if workspace.spec.tenant_id != authorization.tenant_id:
        mismatch("TENANT_BINDING", "workspace tenant does not match authorization")
    if workspace.spec.purpose_id != authorization.purpose_id:
        mismatch("PURPOSE_BINDING", "workspace purpose does not match authorization")
    if projection.projection_id != authorization.projection_id:
        mismatch("PROJECTION_BINDING", "projection id does not match authorization")
    if projection_digest != authorization.projection_digest:
        mismatch("PROJECTION_DIGEST", "projection bytes do not match authorization")
    if projection.source_state_root != authorization.source_state_root:
        mismatch("SOURCE_STATE_BINDING", "projection state root does not match authorization")
    if projection.source_event_position != authorization.source_event_position:
        mismatch("EVENT_POSITION_BINDING", "projection event position does not match authorization")
    if current_state_root != authorization.source_state_root:
        mismatch("STALE_STATE", "authoritative state changed before disclosure")
    if current_authority_state_digest != authorization.authority_state_digest:
        mismatch("STALE_AUTHORITY", "authority state changed before disclosure")

    projected_refs = tuple(sorted(item.ref for item in projection.objects))
    authorized_refs = tuple(sorted(authorization.allowed_object_refs))
    if projected_refs != authorized_refs:
        mismatch("OBJECT_SCOPE", "projection object set exceeds or differs from authorization")

    revoked = sorted(
        set(authorization.authority_basis_refs).intersection(revoked_authority_basis_refs)
    )
    if revoked:
        mismatch(
            "AUTHORITY_REVOKED",
            "authorization basis was revoked: " + ", ".join(revoked),
        )

    if evaluated_at < authorization.issued_at or evaluated_at >= authorization.valid_until:
        mismatch("AUTHORIZATION_TIME", "disclosure authorization is not current")
    if evaluated_at < projection.projected_at or evaluated_at >= projection.expires_at:
        mismatch("PROJECTION_TIME", "governed projection is not current")

    outcome = DisclosureOutcome.DENY if mismatches else DisclosureOutcome.PASS
    provisional = DisclosureAssessment(
        assessment_id=f"disclosure:{authorization.authorization_id}",
        authorization_digest=authorization.authorization_digest,
        projection_digest=projection_digest,
        destination_id=destination_id,
        outcome=outcome,
        mismatches=tuple(mismatches),
        evaluated_at=evaluated_at,
    )
    return provisional.model_copy(
        update={"assessment_digest": provisional.computed_digest}
    )
