from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from ..contracts.common import canonical_digest
from ..contracts.uniform_whisker import GovernedUniform


def _records(value: object) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _ref_tuple(records: Sequence[Mapping[str, Any]], key: str) -> tuple[str, ...]:
    refs = {str(item[key]) for item in records if item.get(key)}
    return tuple(sorted(refs))


def _parse_datetime(raw: object, label: str) -> datetime:
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"{label} is required")
    moment = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if moment.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
    return moment


def _parse_context_time(context: Mapping[str, Any]) -> datetime:
    time_value = context.get("time")
    if not isinstance(time_value, Mapping):
        raise ValueError("execution context time binding is required")
    return _parse_datetime(time_value.get("now"), "execution context time.now")


def _validity_deadline(record: Mapping[str, Any], label: str) -> datetime:
    validity = record.get("validity")
    if not isinstance(validity, Mapping):
        raise ValueError(f"{label} validity is required")
    return _parse_datetime(validity.get("valid_until"), f"{label} valid_until")


def build_governed_uniform(
    context: Mapping[str, Any],
    *,
    uniform_id: str,
    capability: str,
    target: str,
    action_digest: str,
    valid_until: datetime,
    permitted_effect_classes: tuple[str, ...] = (),
    consequence_ref: str | None = None,
    revocation_epoch: int = 0,
) -> GovernedUniform:
    """Project the existing Kernel execution context into a portable uniform.

    This is a projection only. It does not resolve new authority, change state,
    authorize execution, or issue clearance. REHT still consumes authoritative
    execution context independently at the execution boundary.

    Projection is monotonic: it refuses to carry authority for a different
    principal/capability and cannot outlive the selected authority/delegation/
    purpose validity on which the projected context depends.
    """

    tenant_id = context.get("tenant_id")
    actor_id = context.get("actor")
    identity_ref = context.get("identity")
    state_ref = context.get("state_ref")
    if not all(
        isinstance(item, str) and item
        for item in (tenant_id, actor_id, identity_ref, state_ref)
    ):
        raise ValueError(
            "execution context requires tenant, actor, identity and state_ref"
        )

    authorities = _records(context.get("authority"))
    matching_authorities = tuple(
        item
        for item in authorities
        if item.get("principal") == actor_id and item.get("capability") == capability
    )
    authority_refs = _ref_tuple(matching_authorities, "authority_id")
    if not authority_refs:
        raise ValueError(
            "execution context has no authority bound to actor and capability"
        )

    delegations = _records(context.get("delegation"))
    relevant_delegations = tuple(
        item
        for item in delegations
        if item.get("authority_ref") in set(authority_refs)
    )

    purpose = context.get("purpose")
    purpose_ref = (
        str(purpose["purpose_id"])
        if isinstance(purpose, Mapping) and purpose.get("purpose_id")
        else None
    )
    issued_at = _parse_context_time(context)
    if valid_until.utcoffset() is None:
        raise ValueError("uniform valid_until must be timezone-aware")

    dependency_deadlines = [
        *(
            _validity_deadline(item, f"authority {item.get('authority_id', '?')}")
            for item in matching_authorities
        ),
        *(
            _validity_deadline(item, f"delegation {item.get('delegation_id', '?')}")
            for item in relevant_delegations
        ),
    ]
    if isinstance(purpose, Mapping):
        dependency_deadlines.append(_validity_deadline(purpose, "purpose"))
    earliest_deadline = min(dependency_deadlines)
    if valid_until > earliest_deadline:
        raise ValueError(
            "uniform valid_until exceeds shortest authority/delegation/purpose validity"
        )

    return GovernedUniform(
        uniform_id=uniform_id,
        tenant_id=tenant_id,
        actor_id=actor_id,
        identity_ref=identity_ref,
        capability=capability,
        target=target,
        action_digest=action_digest,
        source_context_digest=canonical_digest(dict(context)),
        state_ref=state_ref,
        authority_refs=authority_refs,
        delegation_refs=_ref_tuple(relevant_delegations, "delegation_id"),
        purpose_ref=purpose_ref,
        constraint_refs=_ref_tuple(
            _records(context.get("constraints")), "constraint_id"
        ),
        evidence_refs=_ref_tuple(_records(context.get("evidence")), "evidence_id"),
        permitted_effect_classes=permitted_effect_classes,
        consequence_ref=consequence_ref,
        issued_at=issued_at,
        valid_until=valid_until,
        revocation_epoch=revocation_epoch,
    )
