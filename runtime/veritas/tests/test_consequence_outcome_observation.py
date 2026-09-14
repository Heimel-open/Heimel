from copy import deepcopy

import pytest

from veritas import (
    ConsequenceOutcomeObservationError,
    ConsequenceOutcomeObservationV1,
    VeritasChainService,
    WORMLog,
    consequence_outcome_digest,
)


def payload():
    body = {
        "schema": "heimel.consequence.outcome-observation.v1",
        "consequence_id": "c-1",
        "execution_id": "exec-1",
        "gateway_record_id": "gateway-execution:exec-1",
        "action_digest": "a" * 64,
        "completion_criteria_hash": "sha256:" + "c" * 64,
        "evidence_requirement_hash": "sha256:" + "e" * 64,
        "governed_effect_completed": True,
        "completion_criteria_satisfied": True,
        "required_evidence_verified": True,
        "verified_at": "2026-09-14T04:47:00Z",
        "verifier_id": "heimel-outcome-verifier",
        "verifier_version": "1.0.0",
        "verifier_config_digest": "sha256:" + "f" * 64,
        "authority_granted": False,
    }
    return {**body, "observation_digest": consequence_outcome_digest(body)}


def test_outcome_observation_is_verified_and_stored_in_worm():
    worm = WORMLog()
    service = VeritasChainService(worm)
    service.store_consequence_outcome_observation(payload(), tenant_id="tenant-1")

    assert service.verify_chain() is True
    entry = service.find_entry("outcome:c-1")
    assert entry is not None
    event = entry["observed_events"][0]
    provenance = event["provenance"]
    assert provenance["completion_criteria_hash"] == "sha256:" + "c" * 64
    assert provenance["verifier_id"] == "heimel-outcome-verifier"
    assert provenance["verifier_version"] == "1.0.0"
    assert provenance["verifier_config_digest"] == "sha256:" + "f" * 64
    assert provenance["authority_granted"] is False


def test_tampered_outcome_digest_never_reaches_worm():
    worm = WORMLog()
    service = VeritasChainService(worm)
    tampered = payload()
    tampered["consequence_id"] = "c-2"

    with pytest.raises(ConsequenceOutcomeObservationError, match="digest mismatch"):
        service.store_consequence_outcome_observation(tampered, tenant_id="tenant-1")
    assert worm.read_all() == []


def test_outcome_observation_can_never_grant_authority():
    raw = payload()
    body = {key: value for key, value in raw.items() if key != "observation_digest"}
    body["authority_granted"] = True
    body["observation_digest"] = consequence_outcome_digest(body)

    with pytest.raises(ConsequenceOutcomeObservationError, match="never grant authority"):
        ConsequenceOutcomeObservationV1.verify(body)


def test_verifier_config_digest_is_required_and_hash_bound():
    raw = payload()
    body = {key: value for key, value in raw.items() if key != "observation_digest"}
    body["verifier_config_digest"] = "not-a-digest"
    body["observation_digest"] = consequence_outcome_digest(body)
    with pytest.raises(ConsequenceOutcomeObservationError, match="verifier_config_digest"):
        ConsequenceOutcomeObservationV1.verify(body)
