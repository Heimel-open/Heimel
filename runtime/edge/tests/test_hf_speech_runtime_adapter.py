import pytest

from valo_edge.adapters.hf_speech_runtime import HFSpeechRuntimeAdapter


TIMESTAMP = "2026-08-08T16:40:00Z"


def _event(arguments: str = '{"celsius":21}') -> dict:
    return {
        "type": "response.function_call_arguments.done",
        "event_id": "evt_1",
        "response_id": "resp_1",
        "item_id": "item_1",
        "output_index": 0,
        "call_id": "call_1",
        "name": "set_temperature",
        "arguments": arguments,
    }


def _adapter() -> HFSpeechRuntimeAdapter:
    return HFSpeechRuntimeAdapter(
        device_id="thermostat-1",
        actor_id="speaker:alice",
        actor_attestation_hash="actor-attestation-1",
        model_manifest_hash="model-manifest-1",
    )


def test_completed_function_call_becomes_proposal_only() -> None:
    adapter = _adapter()

    proposal = adapter.proposal_from_event(
        _event(),
        session_id="session-1",
        timestamp_iso=TIMESTAMP,
        transcript_digest="transcript-1",
    )

    assert proposal.proposal_id == "hf-s2s:session-1:call_1"
    assert proposal.device_id == "thermostat-1"
    assert proposal.action_type == "VOICE_TOOL:set_temperature"
    assert proposal.parameters["tool_name"] == "set_temperature"
    assert proposal.parameters["arguments"] == {"celsius": 21}
    assert proposal.parameters["voice_context"] == {
        "runtime": "huggingface/speech-to-speech",
        "protocol": "openai-realtime",
        "session_id": "session-1",
        "event_id": "evt_1",
        "call_id": "call_1",
        "actor_id": "speaker:alice",
        "actor_attestation_hash": "actor-attestation-1",
        "response_id": "resp_1",
        "item_id": "item_1",
        "output_index": 0,
    }
    assert proposal.nonce == "hf-s2s:session-1:evt_1"
    assert proposal.model_manifest_hash == "model-manifest-1"
    assert proposal.sensor_digest == "transcript-1"
    assert not hasattr(adapter, "execute")
    assert not hasattr(adapter, "dispatch")


def test_same_event_and_context_are_deterministic() -> None:
    adapter = _adapter()

    first = adapter.proposal_from_event(
        _event(), session_id="session-1", timestamp_iso=TIMESTAMP
    )
    second = adapter.proposal_from_event(
        _event(), session_id="session-1", timestamp_iso=TIMESTAMP
    )

    assert first.proposal_hash == second.proposal_hash


def test_changed_arguments_change_canonical_proposal_hash() -> None:
    adapter = _adapter()

    first = adapter.proposal_from_event(
        _event('{"celsius":21}'), session_id="session-1", timestamp_iso=TIMESTAMP
    )
    second = adapter.proposal_from_event(
        _event('{"celsius":22}'), session_id="session-1", timestamp_iso=TIMESTAMP
    )

    assert first.proposal_hash != second.proposal_hash


@pytest.mark.parametrize(
    "event",
    [
        {**_event(), "type": "response.output_audio.done"},
        {key: value for key, value in _event().items() if key != "event_id"},
        {key: value for key, value in _event().items() if key != "call_id"},
        {key: value for key, value in _event().items() if key != "name"},
        {**_event(), "arguments": "not-json"},
        {**_event(), "arguments": "[]"},
        {**_event(), "arguments": {"celsius": 21}},
    ],
)
def test_invalid_events_fail_closed(event: dict) -> None:
    with pytest.raises(ValueError):
        _adapter().proposal_from_event(
            event, session_id="session-1", timestamp_iso=TIMESTAMP
        )


def test_identity_and_session_are_required() -> None:
    with pytest.raises(ValueError):
        HFSpeechRuntimeAdapter(device_id="thermostat-1", actor_id="")

    adapter = _adapter()
    with pytest.raises(ValueError):
        adapter.proposal_from_event(_event(), session_id="", timestamp_iso=TIMESTAMP)
