from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from valo_kernel.state_resolution import (
    SourceFactObservation,
    StateFactRequirement,
    authority_state_reference_from_bundle,
    resolve_state_bundle,
    seal_causal_continuity_proof,
)


def test_state_without_provenance_is_inadmissible_for_authorization() -> None:
    now = datetime(2026, 9, 15, 6, 25, tzinfo=UTC)

    with pytest.raises(ValidationError, match="source fact observation fields are required"):
        SourceFactObservation(
            tenant_id="acme",
            source_id="bank-a",
            fact_id="cash:treasury",
            fact_type="AVAILABLE_CASH",
            source_version="bank-a:cash:v12",
            value_digest="a" * 64,
            provenance_ref="",
            effective_at=now - timedelta(seconds=2),
            observed_at=now - timedelta(seconds=1),
            valid_until=now + timedelta(seconds=30),
        )


def test_provenanced_state_can_be_bound_into_authority_reference() -> None:
    now = datetime(2026, 9, 15, 6, 25, tzinfo=UTC)
    observation = SourceFactObservation(
        tenant_id="acme",
        source_id="bank-a",
        fact_id="cash:treasury",
        fact_type="AVAILABLE_CASH",
        source_version="bank-a:cash:v12",
        value_digest="a" * 64,
        provenance_ref="bank-a:account:treasury:v12",
        effective_at=now - timedelta(seconds=2),
        observed_at=now - timedelta(seconds=1),
        valid_until=now + timedelta(seconds=30),
    )
    requirement = StateFactRequirement(
        requirement_id="available-cash",
        source_id="bank-a",
        fact_type="AVAILABLE_CASH",
        max_staleness_seconds=10,
    )
    continuity = seal_causal_continuity_proof(
        tenant_id="acme",
        source_id="bank-a",
        fact_id="cash:treasury",
        observed_version="bank-a:cash:v12",
        checked_version="bank-a:cash:v12:commit",
        status="CONTINUOUS",
        checked_at=now,
        valid_until=now + timedelta(seconds=2),
        proof_ref="bank-a:cash:continuity:commit",
    )

    bundle = resolve_state_bundle(
        tenant_id="acme",
        requirements=(requirement,),
        observations=(observation,),
        continuity_proofs=(continuity,),
        evaluated_at=now,
    )
    reference = authority_state_reference_from_bundle(
        bundle=bundle,
        state_root="c" * 64,
    )

    assert bundle.facts[0].observation.provenance_ref == "bank-a:account:treasury:v12"
    assert reference.dependency_digest == bundle.dependency_digest
    assert reference.valid_until == bundle.valid_until
