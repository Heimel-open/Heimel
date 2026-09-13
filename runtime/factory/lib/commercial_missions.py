"""Bridge commercial-loop evidence into normal Factory OS build orders.

Commercial opportunity state is never execution authority. This bridge only
creates a bounded BuildOrderV1 after explicit customer scope/spec evidence is
present. Normal command-plane validation, worker isolation, QC and merge rules
still apply.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from lib.build_order_intake import BuildOrderV1, Scope
from lib.commercial_loop import CommercialLoop, CommercialState


class CommercialMissionKind(str, Enum):
    POC = "poc"
    PRODUCTION = "production"
    SUPPORT = "support"


_REQUIRED_SOURCE_STATE = {
    CommercialMissionKind.POC: CommercialState.POC_TERMS_ACCEPTED,
    CommercialMissionKind.PRODUCTION: CommercialState.PRODUCTION_SPEC_ACCEPTED,
    CommercialMissionKind.SUPPORT: CommercialState.SERVICE_SIGNAL_OBSERVED,
}


@dataclass(frozen=True)
class CommercialMissionSpec:
    kind: CommercialMissionKind
    customer_ref: str
    spec_ref: str
    spec_digest: str
    target_repo: str
    objective: str
    owned_files: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    dependencies: tuple[str, ...] = ()
    target_base_ref: str = "main"
    canonical_base_sha: str | None = None

    def __post_init__(self) -> None:
        required = {
            "customer_ref": self.customer_ref,
            "spec_ref": self.spec_ref,
            "spec_digest": self.spec_digest,
            "target_repo": self.target_repo,
            "objective": self.objective,
        }
        for name, value in required.items():
            if not value.strip():
                raise ValueError(f"{name} is required")
        if not self.owned_files:
            raise ValueError("owned_files must be bounded and non-empty")
        if not self.acceptance_criteria:
            raise ValueError("acceptance_criteria must be non-empty")


def build_order_from_commercial_spec(
    loop: CommercialLoop,
    spec: CommercialMissionSpec,
    *,
    principal: str,
    authority_basis: str,
    issued_via: str = "commercial-loop",
) -> BuildOrderV1:
    """Create a bounded build order from an accepted commercial scope."""

    expected = _REQUIRED_SOURCE_STATE[spec.kind]
    if loop.state is not expected:
        raise ValueError(
            f"{spec.kind.value} mission requires {expected.value}, got {loop.state.value}"
        )
    if not principal.strip() or not authority_basis.strip():
        raise ValueError("principal and authority_basis are required metadata")

    now = datetime.now(timezone.utc).isoformat()
    stable = "|".join(
        (
            loop.opportunity_id,
            spec.kind.value,
            spec.customer_ref,
            spec.spec_ref,
            spec.spec_digest,
            spec.target_repo,
        )
    )
    key = hashlib.sha256(stable.encode("utf-8")).hexdigest()

    return BuildOrderV1(
        build_order_id=f"commercial-{spec.kind.value}-{key[:16]}",
        issued_at=now,
        principal=principal,
        issued_via=issued_via,
        authority="commercial-mission-request",
        authority_basis=authority_basis,
        source_ref=spec.spec_ref,
        target_repo=spec.target_repo,
        target_base_ref=spec.target_base_ref,
        canonical_base_sha=spec.canonical_base_sha,
        objective=spec.objective,
        owned_files=spec.owned_files,
        scope=Scope(paths=spec.owned_files),
        dependencies=spec.dependencies,
        acceptance_criteria=spec.acceptance_criteria,
        risk_hints=("commercial-customer-delivery", spec.kind.value),
        requires_independent_qc=True,
        requires_receipt=True,
        idempotency_key=key,
        authority_effect="none",
    )


__all__ = [
    "CommercialMissionKind",
    "CommercialMissionSpec",
    "build_order_from_commercial_spec",
]
