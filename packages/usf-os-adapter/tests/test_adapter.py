import pytest

from heimel_usf_os_adapter import AdapterReject, map_usf_os_packet


def valid_envelope():
    return {
        "source_system": "USF-OS",
        "source_version": "2026-public",
        "packet": {
            "object": {"id": "case-17"},
            "boundary": {"scope": "bounded_object"},
            "evidence": {
                "class": "OBSERVED",
                "source_ref": "urn:usf:source:17",
                "observed_at": "2026-09-14T08:00:00Z",
            },
            "unit": "case",
            "current_state": {"status": "open"},
            "required_state": {"status": "closed"},
            "gap": {"status": "unresolved"},
            "residual_owner": "external:owner:17",
            "closure_gate": {"condition": "verified correction"},
            "replay": "required",
            "clocks": {
                "awareness": "2026-09-14T08:00:00Z",
                "duty": "2026-09-14T08:05:00Z",
            },
            "actors": {
                "operator": "external:operator:1",
                "second_operator": "external:operator:2",
                "signer": "external:signer:1",
            },
        },
    }


def test_maps_only_into_non_authoritative_ingress_contract():
    result = map_usf_os_packet(valid_envelope()).as_dict()

    assert result["adapter"] == "heimel.usf_os.v1"
    assert result["canonical"]["state"]["current"] == {"status": "open"}
    assert result["canonical"]["evidence_input"]["status"] == "EXTERNAL_UNVERIFIED"
    assert result["canonical"]["responsibility"]["status"] == "EXTERNAL_REFERENCES_ONLY"
    assert result["admission"] == {
        "status": "MAPPED_NOT_AUTHORIZED",
        "authority": "UNRESOLVED",
        "effect": "UNRESOLVED",
        "evidence": "REQUIRES_HEIMEL_VERIFICATION",
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("authority", {"actor": "external:signer:1"}),
        ("permit", "allow"),
        ("decision", "ALLOW"),
        ("effect", {"tool": "wire_money"}),
        ("consequence_bearing", False),
        ("tool_id", "external-tool"),
    ],
)
def test_rejects_caller_supplied_governed_semantics(field, value):
    envelope = valid_envelope()
    envelope["packet"][field] = value

    with pytest.raises(AdapterReject, match="governed semantics"):
        map_usf_os_packet(envelope)


def test_unknown_packet_field_fails_closed():
    envelope = valid_envelope()
    envelope["packet"]["helpful_extension"] = True

    with pytest.raises(AdapterReject, match="unknown packet fields"):
        map_usf_os_packet(envelope)


def test_unknown_nested_evidence_field_fails_closed():
    envelope = valid_envelope()
    envelope["packet"]["evidence"]["trusted"] = True

    with pytest.raises(AdapterReject, match="unknown evidence fields"):
        map_usf_os_packet(envelope)


def test_open_evidence_cannot_enter_governed_path():
    envelope = valid_envelope()
    envelope["packet"]["evidence"]["class"] = "OPEN"

    with pytest.raises(AdapterReject, match="OPEN evidence"):
        map_usf_os_packet(envelope)


def test_missing_required_field_fails_closed():
    envelope = valid_envelope()
    del envelope["packet"]["closure_gate"]

    with pytest.raises(AdapterReject, match="missing packet fields"):
        map_usf_os_packet(envelope)


def test_replay_must_be_required():
    envelope = valid_envelope()
    envelope["packet"]["replay"] = False

    with pytest.raises(AdapterReject, match="replay must be required"):
        map_usf_os_packet(envelope)


def test_wrong_source_system_is_rejected():
    envelope = valid_envelope()
    envelope["source_system"] = "something-else"

    with pytest.raises(AdapterReject, match="source_system must be USF-OS"):
        map_usf_os_packet(envelope)


def test_actor_refs_remain_external_and_do_not_become_authority():
    result = map_usf_os_packet(valid_envelope()).as_dict()

    refs = result["canonical"]["responsibility"]["actor_refs"]
    assert refs["signer"] == "external:signer:1"
    assert "authority" not in result["canonical"]["responsibility"]
    assert result["admission"]["authority"] == "UNRESOLVED"
