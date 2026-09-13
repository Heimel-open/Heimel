from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from valo_kernel.state_resolution import (
    SourceFactObservation,
    StateFactRequirement,
    authority_state_reference_from_bundle,
    resolve_state_bundle,
    seal_causal_continuity_proof,
)


def _observations(now: datetime) -> tuple[SourceFactObservation, ...]:
    return (
        SourceFactObservation(
            tenant_id="acme",
            source_id="sap",
            fact_id="budget:treasury",
            fact_type="AVAILABLE_BUDGET",
            source_version="sap:budget:v44",
            value_digest="a" * 64,
            provenance_ref="sap:ledger:budget:treasury",
            effective_at=now - timedelta(seconds=4),
            observed_at=now - timedelta(seconds=2),
            valid_until=now + timedelta(seconds=20),
        ),
        SourceFactObservation(
            tenant_id="acme",
            source_id="bank-a",
            fact_id="spend:treasury",
            fact_type="SETTLED_SPEND",
            source_version="bank-a:spend:v101",
            value_digest="b" * 64,
            provenance_ref="bank-a:account:treasury",
            effective_at=now - timedelta(seconds=3),
            observed_at=now - timedelta(seconds=1),
            valid_until=now + timedelta(seconds=10),
        ),
    )


def _requirements() -> tuple[StateFactRequirement, ...]:
    return (
        StateFactRequirement(
            requirement_id="budget",
            source_id="sap",
            fact_type="AVAILABLE_BUDGET",
            max_staleness_seconds=30,
        ),
        StateFactRequirement(
            requirement_id="settled-spend",
            source_id="bank-a",
            fact_type="SETTLED_SPEND",
            max_staleness_seconds=5,
        ),
    )


def _continuous_proofs(now: datetime, observations: tuple[SourceFactObservation, ...]):
    return tuple(
        seal_causal_continuity_proof(
            tenant_id=item.tenant_id,
            source_id=item.source_id,
            fact_id=item.fact_id,
            observed_version=item.source_version,
            checked_version=f"{item.source_version}:commit",
            status="CONTINUOUS",
            checked_at=now,
            valid_until=now + timedelta(seconds=2),
            proof_ref=f"{item.source_id}:continuity:commit",
        )
        for item in observations
    )


def test_resolves_source_bound_facts_without_synthesizing_a_new_truth():
    now = datetime(2026, 8, 16, 9, 30, tzinfo=UTC)
    observations = _observations(now)
    bundle = resolve_state_bundle(
        tenant_id="acme",
        requirements=_requirements(),
        observations=observations,
        continuity_proofs=_continuous_proofs(now, observations),
        evaluated_at=now,
    )

    assert bundle.bundle_digest == bundle.computed_digest
    assert bundle.authority_effect == "NO_AUTHORITY_CREATION"
    assert bundle.can_issue_clearance is False
    assert [item.observation.source_id for item in bundle.facts] == ["sap", "bank-a"]
    assert [item.observation.value_digest for item in bundle.facts] == [
        "a" * 64,
        "b" * 64,
    ]
    assert bundle.valid_until == now + timedelta(seconds=2)


def test_temporal_freshness_is_not_enough_when_causal_continuity_is_invalidated():
    now = datetime(2026, 8, 16, 9, 30, tzinfo=UTC)
    observations = _observations(now)
    good = _continuous_proofs(now, observations)[1]
    invalidated = seal_causal_continuity_proof(
        tenant_id="acme",
        source_id="sap",
        fact_id="budget:treasury",
        observed_version="sap:budget:v44",
        checked_version="sap:budget:v45",
        status="INVALIDATED",
        checked_at=now,
        valid_until=now + timedelta(seconds=2),
        proof_ref="sap:continuity:commit",
        invalidating_refs=("sap:budget-revocation:v45",),
    )

    with pytest.raises(ValueError, match="causal continuity is not established"):
        resolve_state_bundle(
            tenant_id="acme",
            requirements=_requirements(),
            observations=observations,
            continuity_proofs=(invalidated, good),
            evaluated_at=now,
        )


def test_missing_causal_continuity_fails_closed_even_for_recent_fact():
    now = datetime(2026, 8, 16, 9, 30, tzinfo=UTC)
    observations = _observations(now)

    with pytest.raises(ValueError, match="causal continuity proof is required"):
        resolve_state_bundle(
            tenant_id="acme",
            requirements=_requirements(),
            observations=observations,
            continuity_proofs=(),
            evaluated_at=now,
        )


def test_authority_critical_requirement_cannot_disable_causal_continuity():
    with pytest.raises(ValueError, match="authority-critical facts require causal continuity"):
        StateFactRequirement(
            requirement_id="delegation",
            source_id="iam",
            fact_type="DELEGATION",
            authority_critical=True,
            require_causal_continuity=False,
        )


def test_commit_current_requirement_rejects_earlier_continuity_check():
    now = datetime(2026, 8, 16, 9, 30, tzinfo=UTC)
    observations = _observations(now)
    proofs = tuple(
        seal_causal_continuity_proof(
            tenant_id=item.tenant_id,
            source_id=item.source_id,
            fact_id=item.fact_id,
            observed_version=item.source_version,
            checked_version=item.source_version,
            status="CONTINUOUS",
            checked_at=now - timedelta(milliseconds=1),
            valid_until=now + timedelta(seconds=2),
            proof_ref=f"{item.source_id}:continuity:early",
        )
        for item in observations
    )

    with pytest.raises(ValueError, match="not checked at commit evaluation"):
        resolve_state_bundle(
            tenant_id="acme",
            requirements=_requirements(),
            observations=observations,
            continuity_proofs=proofs,
            evaluated_at=now,
        )


def test_bounded_staleness_remains_independent_of_causal_continuity():
    now = datetime(2026, 8, 16, 9, 30, tzinfo=UTC)
    old_budget = SourceFactObservation(
        tenant_id="acme",
        source_id="sap",
        fact_id="budget:treasury",
        fact_type="AVAILABLE_BUDGET",
        source_version="sap:budget:v44",
        value_digest="a" * 64,
        provenance_ref="sap:ledger:budget:treasury",
        effective_at=now - timedelta(minutes=2),
        observed_at=now - timedelta(seconds=31),
        valid_until=now + timedelta(seconds=20),
    )
    observations = (old_budget, _observations(now)[1])

    with pytest.raises(ValueError, match="exceeds bounded staleness"):
        resolve_state_bundle(
            tenant_id="acme",
            requirements=_requirements(),
            observations=observations,
            continuity_proofs=_continuous_proofs(now, observations),
            evaluated_at=now,
        )


def test_observed_source_version_must_match_continuity_proof():
    now = datetime(2026, 8, 16, 9, 30, tzinfo=UTC)
    observations = _observations(now)
    proofs = list(_continuous_proofs(now, observations))
    proofs[0] = seal_causal_continuity_proof(
        tenant_id="acme",
        source_id="sap",
        fact_id="budget:treasury",
        observed_version="sap:budget:v43",
        checked_version="sap:budget:v44",
        status="CONTINUOUS",
        checked_at=now,
        valid_until=now + timedelta(seconds=2),
        proof_ref="sap:continuity:wrong-base",
    )

    with pytest.raises(ValueError, match="causal continuity version mismatch"):
        resolve_state_bundle(
            tenant_id="acme",
            requirements=_requirements(),
            observations=observations,
            continuity_proofs=tuple(proofs),
            evaluated_at=now,
        )


def test_state_bundle_can_be_reduced_to_opaque_authority_state_reference():
    now = datetime(2026, 8, 16, 9, 30, tzinfo=UTC)
    observations = _observations(now)
    bundle = resolve_state_bundle(
        tenant_id="acme",
        requirements=_requirements(),
        observations=observations,
        continuity_proofs=_continuous_proofs(now, observations),
        evaluated_at=now,
    )
    reference = authority_state_reference_from_bundle(
        bundle=bundle,
        state_root="c" * 64,
    )

    assert reference.tenant_id == "acme"
    assert reference.state_root == "c" * 64
    assert reference.dependency_digest == bundle.dependency_digest
    assert reference.observed_at == now - timedelta(seconds=2)
    assert reference.valid_until == bundle.valid_until
    assert "value_digest" not in reference.model_dump(mode="json")
