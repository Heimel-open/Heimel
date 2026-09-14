from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum


class DeploymentConformanceError(ValueError):
    pass


class GrantKind(str, Enum):
    API_CREDENTIAL = "API_CREDENTIAL"
    IAM_PERMISSION = "IAM_PERMISSION"
    DATABASE_WRITE = "DATABASE_WRITE"
    SERVICE_ACCOUNT = "SERVICE_ACCOUNT"
    NETWORK_PATH = "NETWORK_PATH"
    HUMAN_ADMIN = "HUMAN_ADMIN"


@dataclass(frozen=True)
class EffectGrant:
    principal: str
    effect_target: str
    kind: GrantKind
    consequence_capable: bool = True


@dataclass(frozen=True)
class DeploymentConformanceResult:
    conformant: bool
    violations: tuple[EffectGrant, ...]


def verify_no_direct_effect_path(
    grants: Iterable[EffectGrant], *, gateway_principals: Iterable[str]
) -> DeploymentConformanceResult:
    """Fail closed if a non-Gateway principal can reach a consequence target.

    This is deployment-level conformance, not source inspection. Callers should
    build ``grants`` from the effective IAM/network/credential inventory of the
    deployed system. Any consequence-capable grant outside the named Gateway
    principals is a NO_DIRECT_EFFECT_PATH violation.
    """
    allowed = frozenset(gateway_principals)
    if not allowed:
        raise DeploymentConformanceError("at least one Gateway principal is required")

    violations = tuple(
        grant
        for grant in grants
        if grant.consequence_capable and grant.principal not in allowed
    )
    return DeploymentConformanceResult(
        conformant=not violations,
        violations=violations,
    )


def require_no_direct_effect_path(
    grants: Iterable[EffectGrant], *, gateway_principals: Iterable[str]
) -> None:
    result = verify_no_direct_effect_path(grants, gateway_principals=gateway_principals)
    if result.violations:
        rendered = ", ".join(
            f"{g.principal}->{g.effect_target}({g.kind.value})" for g in result.violations
        )
        raise DeploymentConformanceError(
            "NO_DIRECT_EFFECT_PATH deployment violation: " + rendered
        )


__all__ = [
    "DeploymentConformanceError",
    "DeploymentConformanceResult",
    "EffectGrant",
    "GrantKind",
    "require_no_direct_effect_path",
    "verify_no_direct_effect_path",
]
