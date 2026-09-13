import pytest

from src.valo_platform.advisor_fabric import (
    AdvisorAuthorityBoundary,
    AdvisorConsentBasis,
    AdvisorContextGateway,
    AdvisorContextRef,
    AdvisorContextScope,
    AdvisorMemoryPolicy,
    AdvisorMemoryRef,
)


def _context_ref(source_type: str = "scout_signal") -> AdvisorContextRef:
    return AdvisorContextRef(
        ref_id="ctx-1",
        source_type=source_type,
        scope=AdvisorContextScope.TENANT,
        consent_basis=AdvisorConsentBasis.CUSTOMER_CONSENT,
        source_ref="scout:signal:1",
        evidence_refs=["evidence:1"],
    )


def test_gateway_builds_advisory_context_package() -> None:
    package = AdvisorContextGateway().build_package(
        package_id="pkg-1",
        role="ciso",
        context_refs=[
            _context_ref("scout_signal"),
            AdvisorContextRef(
                ref_id="ctx-2",
                source_type="baro_evidence",
                scope=AdvisorContextScope.TENANT,
                consent_basis=AdvisorConsentBasis.INTERNAL_OPERATIONAL,
                source_ref="baro:evidence:2",
                evidence_refs=["evidence:2"],
            ),
        ],
        memory_refs=[
            AdvisorMemoryRef(
                ref_id="mem-1",
                scope=AdvisorContextScope.TENANT,
                memory_policy=AdvisorMemoryPolicy.TENANT_SCOPED,
                source_ref="enterprise-memory:ciso:tenant-1",
                evidence_refs=["memory:evidence:1"],
            )
        ],
        limitations=["No direct production store read in gateway facade."],
    )

    assert package.advisor_id == "advisor-ciso"
    assert package.role == "ciso"
    assert len(package.context_refs) == 2
    assert len(package.memory_refs) == 1
    assert package.authority_boundary == AdvisorAuthorityBoundary.ADVISORY_ONLY


def test_gateway_rejects_context_not_allowed_by_profile() -> None:
    with pytest.raises(ValueError, match="context source not allowed"):
        AdvisorContextGateway().build_package(
            package_id="pkg-2",
            role="cfo",
            context_refs=[_context_ref("private_calendar")],
        )


def test_gateway_requires_evidence_for_context_refs() -> None:
    with pytest.raises(ValueError, match="context refs require evidence refs"):
        AdvisorContextGateway().build_package(
            package_id="pkg-3",
            role="coo",
            context_refs=[
                AdvisorContextRef(
                    ref_id="ctx-no-evidence",
                    source_type="enterprise_context",
                    scope=AdvisorContextScope.TENANT,
                    consent_basis=AdvisorConsentBasis.PRODUCT_TOS,
                    source_ref="enterprise:context:1",
                )
            ],
        )


def test_memory_refs_must_match_profile_policy() -> None:
    with pytest.raises(ValueError, match="memory refs violate profile memory policy"):
        AdvisorContextGateway().build_package(
            package_id="pkg-4",
            role="chro",
            context_refs=[_context_ref()],
            memory_refs=[
                AdvisorMemoryRef(
                    ref_id="mem-session",
                    scope=AdvisorContextScope.SESSION,
                    memory_policy=AdvisorMemoryPolicy.SESSION,
                    source_ref="session-memory:1",
                    evidence_refs=["memory:evidence:1"],
                )
            ],
        )


def test_tenant_scoped_memory_cannot_claim_public_scope() -> None:
    with pytest.raises(ValueError, match="tenant-scoped memory cannot use public scope"):
        AdvisorMemoryRef(
            ref_id="mem-public",
            scope=AdvisorContextScope.PUBLIC,
            memory_policy=AdvisorMemoryPolicy.TENANT_SCOPED,
            source_ref="enterprise-memory:public",
        )


def test_unknown_role_fails_closed() -> None:
    with pytest.raises(KeyError, match="unknown advisor role"):
        AdvisorContextGateway().build_package(
            package_id="pkg-5",
            role="unknown",
            context_refs=[_context_ref()],
        )


def test_context_gateway_does_not_expose_execution_authority_fields() -> None:
    forbidden_fields = {
        "clearance_id",
        "permit_id",
        "decision",
        "authorized",
        "can_execute",
        "allowed_to_execute",
        "execution_authorized",
    }

    for model in (AdvisorContextRef, AdvisorMemoryRef):
        assert forbidden_fields.isdisjoint(model.model_fields)
