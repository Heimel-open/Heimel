from __future__ import annotations

from valo_kernel.contracts import (
    AdmissionCandidate,
    AdmissionPolicy,
    CanonicalEvent,
    EventType,
    Fact,
    TruthStatus,
    utcnow,
)
from valo_kernel.kernel import create_admission_event

from .conftest import admit_evidence, entity_event, evidence_event, make_provenance


def test_evidence_received_then_admitted(engine) -> None:
    engine.append(entity_event("tenant-a", "worker-1"))
    engine.append(evidence_event("tenant-a", "ev-1", "worker-1"))
    assert engine.state().evidence["ev-1"].status.value == "RECEIVED"

    admit_evidence(engine, "ev-1")
    assert engine.state().evidence["ev-1"].status.value == "ADMITTED"


def test_evidence_is_not_state(engine) -> None:
    """A document asserting 'worker certified' must NOT set worker.certified.
    Evidence requires the full verify -> admit -> derived state event flow."""
    engine.append(entity_event("tenant-a", "worker-1"))
    engine.append(evidence_event("tenant-a", "ev-cert", "worker-1"))
    admit_evidence(engine, "ev-cert")
    facts = engine.state().facts
    assert all(f.predicate != "certified" for f in facts.values())

    # The correct flow: an explicit derived state event.
    engine.append(
        CanonicalEvent(
            event_id="fact-cert",
            event_type=EventType.FACT_ASSERTED,
            tenant_id="tenant-a",
            subject="worker-1",
            source="kernel",
            effective_at=utcnow(),
            payload={
                "fact": Fact(
                    fact_id="f-cert",
                    subject="worker-1",
                    predicate="certified",
                    object="true",
                    tenant_id="tenant-a",
                    provenance=make_provenance("f-cert"),
                )
            },
            evidence_refs=["ev-cert"],
        )
    )
    assert engine.state().facts["f-cert"].truth_status == TruthStatus.ASSERTED


def test_evidence_rejected_and_superseded(engine) -> None:
    engine.append(entity_event("tenant-a", "worker-1"))
    engine.append(evidence_event("tenant-a", "ev-1", "worker-1"))
    evidence = engine.state().evidence["ev-1"]
    candidate = AdmissionCandidate(
        candidate_id="candidate-reject",
        tenant_id="tenant-a",
        evidence_id="ev-1",
        material_type=evidence.type,
        source_fingerprint=evidence.integrity_hash,
        subject_refs=(evidence.subject,),
        entity_refs=(evidence.subject,),
        provenance_refs=(f"source:{evidence.source}",),
        captured_at=evidence.captured_at,
    )
    policy = AdmissionPolicy(
        policy_id="documents-not-allowed",
        tenant_id="tenant-a",
        allowed_material_types=("receipt",),
    )
    engine.append(
        create_admission_event(
            engine.state(),
            candidate,
            policy,
            event_id="reject-ev-1",
        )
    )
    assert engine.state().evidence["ev-1"].status.value == "REJECTED"
