from valo_edge.contracts import (
    CONTRACT_VERSION,
    ConsequenceDecision,
    EdgeActionCommitmentV1,
    EdgeClearanceV1,
    EdgeEnforcementV1,
    EdgeEvidenceV1,
    EdgeObservationV1,
    canonical_json_bytes,
)


def _proposal() -> EdgeActionCommitmentV1:
    return EdgeActionCommitmentV1(
        proposal_id="proposal-001",
        device_id="pump-7",
        action_type="SET_FLOW",
        parameters={"litres_per_minute": 2.5, "enabled": True},
        model_hash="sha256:model",
        firmware_hash="sha256:firmware",
        runtime_hash="sha256:runtime",
        sensor_evidence_digest="sha256:sensors",
        physical_state_digest="sha256:state",
        authority_envelope_digest="sha256:authority",
        boot_epoch="boot-44",
        sequence=17,
        nonce="nonce-001",
        issued_at_iso="2026-08-05T09:00:00Z",
        valid_until_iso="2026-08-05T09:00:05Z",
        signer_key_id="device-key-7",
    )


def test_contract_version_is_explicit():
    assert _proposal().contract_version == CONTRACT_VERSION


def test_canonical_digest_is_stable_across_parameter_order():
    left = _proposal()
    right = _proposal().model_copy(update={"parameters": {"enabled": True, "litres_per_minute": 2.5}})
    assert left.compute_digest() == right.compute_digest()


def test_signature_is_not_part_of_signed_payload():
    proposal = _proposal()
    unsigned = proposal.compute_digest()
    signed = proposal.model_copy(update={
        "signature": {"algorithm": "Ed25519", "key_id": "device-key-7", "signature": "base64:sig"}
    })
    assert signed.compute_digest() == unsigned


def test_consequence_objects_are_separate_and_bound_by_digest():
    proposal = _proposal()
    evidence = EdgeEvidenceV1(
        evidence_id="evidence-001",
        proposal_digest=proposal.compute_digest(),
        device_attestation_digest="sha256:attestation",
        model_hash=proposal.model_hash,
        firmware_hash=proposal.firmware_hash,
        runtime_hash=proposal.runtime_hash,
        sensor_sources=["camera:kitchen-01", "interlock:door-2"],
        observed_state={"door_closed": True},
        observed_at_iso="2026-08-05T09:00:01Z",
        freshness_ms=25,
        completeness=True,
        producer_id="edge-vaig-1",
    )
    clearance = EdgeClearanceV1(
        clearance_id="clearance-001",
        proposal_digest=proposal.compute_digest(),
        evidence_digest=evidence.compute_digest(),
        authority_envelope_digest=proposal.authority_envelope_digest,
        decision=ConsequenceDecision.ALLOW,
        reason_codes=["SCOPE_OK", "STATE_OK"],
        issued_at_iso="2026-08-05T09:00:01Z",
        valid_until_iso="2026-08-05T09:00:03Z",
        boot_epoch=proposal.boot_epoch,
        sequence=proposal.sequence,
        permit_id="permit-001",
        permit_uses=1,
        signer_key_id="micro-reht-key-1",
    )
    enforcement = EdgeEnforcementV1(
        enforcement_id="enforcement-001",
        proposal_digest=proposal.compute_digest(),
        clearance_digest=clearance.compute_digest(),
        device_command_digest="sha256:command",
        permit_id="permit-001",
        permit_use_index=0,
        accepted=True,
        gateway_id="gateway-1",
        enforced_at_iso="2026-08-05T09:00:02Z",
    )
    observation = EdgeObservationV1(
        observation_id="observation-001",
        enforcement_digest=enforcement.compute_digest(),
        device_id=proposal.device_id,
        outcome="EXECUTED",
        observed_output={"actual_flow": 2.48},
        observed_at_iso="2026-08-05T09:00:02Z",
    )

    assert evidence.proposal_digest == proposal.compute_digest()
    assert clearance.evidence_digest == evidence.compute_digest()
    assert enforcement.clearance_digest == clearance.compute_digest()
    assert observation.enforcement_digest == enforcement.compute_digest()


def test_canonical_json_is_utf8_and_compact():
    payload = canonical_json_bytes({"ø": "verdi", "b": 2, "a": 1})
    assert payload == '{"a":1,"b":2,"ø":"verdi"}'.encode("utf-8")
