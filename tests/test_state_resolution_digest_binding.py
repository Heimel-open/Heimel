from datetime import UTC, datetime, timedelta

from valo_kernel.state_resolution import (
    SourceFactObservation,
    StateFactRequirement,
    resolve_state_bundle,
    seal_causal_continuity_proof,
)


def test_dependency_digest_binds_causal_continuity_evidence():
    now = datetime(2026, 8, 16, 9, 45, tzinfo=UTC)
    requirement = StateFactRequirement(
        requirement_id="delegation",
        source_id="iam",
        fact_type="DELEGATION",
        max_staleness_seconds=10,
    )
    observation = SourceFactObservation(
        tenant_id="acme",
        source_id="iam",
        fact_id="delegation:cfo:agent",
        fact_type="DELEGATION",
        source_version="iam:v7",
        value_digest="d" * 64,
        provenance_ref="iam:delegation:cfo:agent",
        effective_at=now - timedelta(seconds=2),
        observed_at=now - timedelta(seconds=1),
        valid_until=now + timedelta(seconds=20),
    )

    def resolve(proof_ref: str):
        proof = seal_causal_continuity_proof(
            tenant_id="acme",
            source_id="iam",
            fact_id="delegation:cfo:agent",
            observed_version="iam:v7",
            checked_version="iam:v7",
            status="CONTINUOUS",
            checked_at=now,
            valid_until=now + timedelta(seconds=2),
            proof_ref=proof_ref,
        )
        return resolve_state_bundle(
            tenant_id="acme",
            requirements=(requirement,),
            observations=(observation,),
            continuity_proofs=(proof,),
            evaluated_at=now,
        )

    first = resolve("iam:continuity:receipt:1")
    second = resolve("iam:continuity:receipt:2")

    assert first.continuity_digest != second.continuity_digest
    assert first.dependency_digest != second.dependency_digest
    assert first.bundle_digest != second.bundle_digest
