from datetime import UTC, datetime, timedelta

import pytest

from valo_kernel.contracts import (
    ConcentrationBasis,
    DependencyDomain,
    DependencyEvidenceStatus,
    DiversityDisposition,
    seal_dependency_reference,
    seal_route_dependency_topology,
)
from valo_kernel.dependency_risk import (
    DEFAULT_DEPENDENCY_DOMAINS,
    assess_dependency_diversity,
)

NOW = datetime(2026, 8, 16, 11, 0, tzinfo=UTC)


def _route(
    route_id: str,
    *,
    overrides: dict[DependencyDomain, tuple[str, str]] | None = None,
    incomplete: tuple[DependencyDomain, ...] = (),
    stale: tuple[DependencyDomain, ...] = (),
):
    overrides = overrides or {}
    dependencies = []
    for index, domain in enumerate(DEFAULT_DEPENDENCY_DOMAINS):
        dependency_id, controller_ref = overrides.get(
            domain,
            (f"{route_id}-{domain.value.lower()}", f"{route_id}-controller-{index}"),
        )
        observed_at = NOW - timedelta(minutes=5)
        valid_until = NOW - timedelta(seconds=1) if domain in stale else NOW + timedelta(hours=1)
        dependencies.append(
            seal_dependency_reference(
                domain=domain,
                dependency_id=dependency_id,
                controller_ref=controller_ref,
                evidence_ref=f"evidence:{route_id}:{domain.value}",
                evidence_digest=f"{index + 1:064x}",
                observed_at=observed_at,
                valid_until=valid_until,
                status=DependencyEvidenceStatus.VERIFIED,
            )
        )
    complete_domains = tuple(
        domain for domain in DEFAULT_DEPENDENCY_DOMAINS if domain not in incomplete
    )
    return seal_route_dependency_topology(
        route_id=route_id,
        dependencies=tuple(dependencies),
        complete_domains=complete_domains,
    )


def test_independent_routes_require_cross_domain_diversity():
    report = assess_dependency_diversity(
        routes=(_route("route-a"), _route("route-b")),
        evaluated_at=NOW,
    )

    assert report.disposition is DiversityDisposition.INDEPENDENT
    assert report.independent is True
    assert report.findings == ()
    assert report.incomplete_domains == ()
    assert report.max_concentration_bps == 5000
    assert report.report_digest == report.computed_digest
    assert report.can_issue_clearance is False


def test_different_providers_with_same_controller_are_not_independent():
    route_a = _route(
        "route-a",
        overrides={DependencyDomain.PROVIDER: ("provider-a", "parent-cloud")},
    )
    route_b = _route(
        "route-b",
        overrides={DependencyDomain.PROVIDER: ("provider-b", "parent-cloud")},
    )

    report = assess_dependency_diversity(routes=(route_a, route_b), evaluated_at=NOW)

    assert report.disposition is DiversityDisposition.CONCENTRATED
    assert report.independent is False
    assert report.max_concentration_bps == 10000
    assert any(
        finding.basis is ConcentrationBasis.CONTROLLER
        and finding.domain is DependencyDomain.PROVIDER
        and finding.shared_ref == "parent-cloud"
        for finding in report.findings
    )


def test_shared_authority_source_refutes_redundancy():
    shared = ("authority-ledger-1", "authority-owner-1")
    route_a = _route(
        "route-a", overrides={DependencyDomain.AUTHORITY_SOURCE: shared}
    )
    route_b = _route(
        "route-b", overrides={DependencyDomain.AUTHORITY_SOURCE: shared}
    )

    report = assess_dependency_diversity(routes=(route_a, route_b), evaluated_at=NOW)

    assert report.disposition is DiversityDisposition.CONCENTRATED
    assert any(
        finding.basis is ConcentrationBasis.DEPENDENCY
        and finding.domain is DependencyDomain.AUTHORITY_SOURCE
        and finding.shared_ref == "authority-ledger-1"
        for finding in report.findings
    )


def test_unknown_completeness_or_stale_evidence_fails_closed():
    route_a = _route("route-a", incomplete=(DependencyDomain.RECOVERY_PATH,))
    route_b = _route("route-b", stale=(DependencyDomain.JURISDICTION,))

    report = assess_dependency_diversity(routes=(route_a, route_b), evaluated_at=NOW)

    assert report.disposition is DiversityDisposition.INDETERMINATE
    assert report.independent is False
    assert "route-a:RECOVERY_PATH" in report.incomplete_domains
    assert "route-b:JURISDICTION" in report.incomplete_domains
    assert any(reason.startswith("DOMAIN_NOT_DECLARED_COMPLETE:") for reason in report.reasons)
    assert any(reason.startswith("DEPENDENCY_NOT_FRESH:") for reason in report.reasons)


def test_route_order_does_not_change_report_digest():
    route_a = _route("route-a")
    route_b = _route("route-b")

    first = assess_dependency_diversity(
        routes=(route_a, route_b),
        evaluated_at=NOW,
    )
    second = assess_dependency_diversity(
        routes=(route_b, route_a),
        evaluated_at=NOW,
    )

    assert first.report_digest == second.report_digest


def test_unsealed_topology_is_rejected():
    route = _route("route-a")
    unsealed = route.model_copy(update={"topology_digest": ""})

    with pytest.raises(ValueError, match="unsealed or tampered"):
        assess_dependency_diversity(
            routes=(unsealed, _route("route-b")),
            evaluated_at=NOW,
        )
