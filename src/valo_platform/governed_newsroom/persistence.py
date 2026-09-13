"""Persistence helpers for Governed Newsroom shadow evaluations."""

from __future__ import annotations

from typing import Dict

from src.valo_platform.canonical import canonical_bytes, canonical_digest
from src.valo_platform.verification_factory.models import VerificationCase, VersionedRef
from src.valo_platform.verification_factory.store import (
    RecordNotFoundError,
    SQLiteVerificationStore,
)

from .models import NewsroomShadowEvaluation


def _ref(artifact_id: str, version: str, value: object) -> VersionedRef:
    return VersionedRef(
        artifact_id=artifact_id,
        version=version,
        reference=f"valo://newsroom/{artifact_id}/{version}",
        digest=canonical_digest(value),
    )


def persist_newsroom_shadow(
    store: SQLiteVerificationStore,
    *,
    case: VerificationCase,
    evaluation: NewsroomShadowEvaluation,
) -> Dict[str, object]:
    """Persist exact artifacts, event and checkpoint for replay."""

    try:
        case_state = store.get_case(case.case_id)
    except RecordNotFoundError:
        store.create_case(case)
        case_state = store.get_case(case.case_id)

    if evaluation.case_id != case.case_id:
        raise ValueError("Evaluation belongs to another case")

    package_ref = _ref(
        evaluation.evidence_package.package_id,
        evaluation.evidence_package.package_version,
        evaluation.evidence_package,
    )
    admissibility_ref = _ref(
        evaluation.admissibility.admissibility_id,
        "v1",
        evaluation.admissibility,
    )
    evaluation_ref = _ref(
        f"newsroom-evaluation:{evaluation.case_id}:{evaluation.claim_id}",
        "v1",
        evaluation,
    )

    for reference, value in (
        (package_ref, evaluation.evidence_package),
        (admissibility_ref, evaluation.admissibility),
        (evaluation_ref, evaluation),
    ):
        payload = canonical_bytes(value)
        store.put_artifact(reference, payload, reference.digest)

    for card in evaluation.public_integrity_cards:
        card_ref = _ref(f"integrity-card:{card.source_id}", "v1", card)
        store.put_artifact(card_ref, canonical_bytes(card), card_ref.digest)

    event = store.append_event(
        case.case_id,
        int(case_state["version"]),
        "NEWSROOM_SHADOW_EVALUATED",
        {
            "evaluation_ref": evaluation_ref.model_dump(mode="json"),
            "evidence_package_ref": package_ref.model_dump(mode="json"),
            "admissibility_ref": admissibility_ref.model_dump(mode="json"),
            "shadow_reht_recommendation": evaluation.shadow_reht_recommendation.value,
        },
    )
    checkpoint = store.put_checkpoint(
        case.case_id,
        "NEWSROOM_EVIDENCE_READY",
        {
            "evaluation_ref": evaluation_ref.model_dump(mode="json"),
            "package_digest": evaluation.evidence_package.package_digest,
            "recommendation": evaluation.shadow_reht_recommendation.value,
        },
        expected_version=event.version,
    )

    return {
        "evaluation_ref": evaluation_ref,
        "evidence_package_ref": package_ref,
        "admissibility_ref": admissibility_ref,
        "event_version": event.version,
        "checkpoint_version": checkpoint.version,
        "event_chain_digest": event.chain_digest,
        "checkpoint_digest": checkpoint.state_digest,
    }


__all__ = ["persist_newsroom_shadow"]
