from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from .contracts import (
    ConcentrationBasis,
    ConcentrationFinding,
    DependencyDiversityReport,
    DependencyDomain,
    DependencyEvidenceStatus,
    DiversityDisposition,
    RouteDependencyTopology,
    canonical_digest,
)

DEFAULT_DEPENDENCY_DOMAINS: tuple[DependencyDomain, ...] = tuple(
    sorted(DependencyDomain, key=lambda item: item.value)
)


def assess_dependency_diversity(
    *,
    routes: tuple[RouteDependencyTopology, ...],
    evaluated_at: datetime,
    required_domains: tuple[DependencyDomain, ...] = DEFAULT_DEPENDENCY_DOMAINS,
) -> DependencyDiversityReport:
    if not required_domains:
        raise ValueError("required dependency domains cannot be empty")

    required_domains = tuple(sorted(required_domains, key=lambda item: item.value))
    if len(set(required_domains)) != len(required_domains):
        raise ValueError("required dependency domains must be unique")

    route_ids = [route.route_id for route in routes]
    if len(set(route_ids)) != len(route_ids):
        raise ValueError("route ids must be unique")

    for route in routes:
        if not route.topology_digest or route.topology_digest != route.computed_digest:
            raise ValueError("route dependency topology is unsealed or tampered")
        for reference in route.dependencies:
            if (
                not reference.reference_digest
                or reference.reference_digest != reference.computed_digest
            ):
                raise ValueError("dependency reference is unsealed or tampered")

    reasons: set[str] = set()
    incomplete_domains: set[str] = set()
    valid_by_domain: dict[
        DependencyDomain, list[tuple[str, str, str]]
    ] = defaultdict(list)

    if len(routes) < 2:
        reasons.add("INSUFFICIENT_ROUTES")

    for route in routes:
        complete_domains = set(route.complete_domains)
        by_domain = defaultdict(list)
        for reference in route.dependencies:
            by_domain[reference.domain].append(reference)

        for domain in required_domains:
            domain_key = f"{route.route_id}:{domain.value}"
            references = by_domain.get(domain, [])
            if domain not in complete_domains:
                incomplete_domains.add(domain_key)
                reasons.add(f"DOMAIN_NOT_DECLARED_COMPLETE:{domain_key}")
                continue
            if not references:
                incomplete_domains.add(domain_key)
                reasons.add(f"MISSING_DOMAIN_EVIDENCE:{domain_key}")
                continue

            domain_valid = True
            for reference in references:
                if reference.status is not DependencyEvidenceStatus.VERIFIED:
                    domain_valid = False
                    reasons.add(
                        "DEPENDENCY_NOT_VERIFIED:"
                        f"{route.route_id}:{domain.value}:{reference.dependency_id}:"
                        f"{reference.status.value}"
                    )
                if not (reference.observed_at <= evaluated_at < reference.valid_until):
                    domain_valid = False
                    reasons.add(
                        "DEPENDENCY_NOT_FRESH:"
                        f"{route.route_id}:{domain.value}:{reference.dependency_id}"
                    )

            if not domain_valid:
                incomplete_domains.add(domain_key)
                continue

            for reference in references:
                valid_by_domain[domain].append(
                    (route.route_id, reference.dependency_id, reference.controller_ref)
                )

    findings: list[ConcentrationFinding] = []
    max_group_size = 0

    for domain in required_domains:
        entries = valid_by_domain.get(domain, [])
        dependency_routes: dict[str, set[str]] = defaultdict(set)
        controller_routes: dict[str, set[str]] = defaultdict(set)
        for route_id, dependency_id, controller_ref in entries:
            dependency_routes[dependency_id].add(route_id)
            controller_routes[controller_ref].add(route_id)

        for basis, groups in (
            (ConcentrationBasis.DEPENDENCY, dependency_routes),
            (ConcentrationBasis.CONTROLLER, controller_routes),
        ):
            for shared_ref, affected_routes in groups.items():
                max_group_size = max(max_group_size, len(affected_routes))
                if len(affected_routes) < 2:
                    continue
                route_tuple = tuple(sorted(affected_routes))
                findings.append(
                    ConcentrationFinding(
                        basis=basis,
                        domain=domain,
                        shared_ref=shared_ref,
                        route_ids=route_tuple,
                    )
                )
                reasons.add(
                    f"SHARED_{basis.value}:{domain.value}:{shared_ref}:"
                    f"{','.join(route_tuple)}"
                )

    findings.sort(
        key=lambda item: (
            item.domain.value,
            item.basis.value,
            item.shared_ref,
            item.route_ids,
        )
    )

    if routes:
        max_concentration_bps = (max_group_size * 10000) // len(routes)
    else:
        max_concentration_bps = 0

    if (reasons and incomplete_domains) or len(routes) < 2:
        disposition = DiversityDisposition.INDETERMINATE
    elif findings:
        disposition = DiversityDisposition.CONCENTRATED
    else:
        disposition = DiversityDisposition.INDEPENDENT

    topology_digests = tuple(sorted(route.topology_digest for route in routes))
    report_data = {
        "topology_digests": topology_digests,
        "required_domains": required_domains,
        "evaluated_at": evaluated_at,
        "disposition": disposition,
        "independent": disposition is DiversityDisposition.INDEPENDENT,
        "findings": tuple(findings),
        "incomplete_domains": tuple(sorted(incomplete_domains)),
        "max_concentration_bps": max_concentration_bps,
        "reasons": tuple(sorted(reasons)),
    }
    provisional = DependencyDiversityReport.model_validate(report_data)
    return DependencyDiversityReport.model_validate(
        {
            **provisional.model_dump(mode="python"),
            "report_digest": canonical_digest(provisional.canonical_payload()),
        }
    )
