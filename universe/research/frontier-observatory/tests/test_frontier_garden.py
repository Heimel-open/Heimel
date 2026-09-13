import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "frontier_garden.py"

spec = importlib.util.spec_from_file_location("frontier_garden", SCRIPT)
frontier_garden = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(frontier_garden)


def test_registry_validates_and_has_seed_frontiers():
    data = frontier_garden.load_registry()
    assert frontier_garden.validate_registry(data, root=ROOT) == []
    assert len(data["frontiers"]) >= 20
    assert len({item["id"] for item in data["frontiers"]}) == len(data["frontiers"])


def test_2026_08_21_synthesis_frontiers_are_registered():
    data = frontier_garden.load_registry()
    expected = {f"FG-{number:03d}" for number in range(11, 21)}
    registered = {item["id"] for item in data["frontiers"]}
    assert expected <= registered

    synthesis = ROOT / "frontier_garden" / "research_synthesis_2026-08-21.md"
    assert synthesis.exists()
    for frontier_id in expected:
        frontier = frontier_garden.frontier_by_id(data, frontier_id)
        assert any(source["path"] == "frontier_garden/research_synthesis_2026-08-21.md" for source in frontier["source_refs"])


def test_every_seed_is_source_grounded():
    data = frontier_garden.load_registry()
    for frontier in data["frontiers"]:
        assert frontier["source_refs"]
        for source in frontier["source_refs"]:
            assert (ROOT / source["path"]).exists()
            assert source["purpose"].strip()


def test_packet_is_single_frontier_and_non_authoritative():
    data = frontier_garden.load_registry()
    packet = frontier_garden.build_packet(data, "FG-008", "SYNAPSE")

    assert packet["protocol"] == "tofoo-frontier-garden-v1"
    assert packet["standing"] == "INFORMATIVE_RESEARCH_ONLY"
    assert packet["frontier"]["id"] == "FG-008"
    assert packet["role"] == "SYNAPSE"
    assert packet["source_refs"] == packet["frontier"]["source_refs"]
    assert "frontiers" not in packet
    assert all("authority" not in key.lower() for key in packet.keys())
    assert any("cannot update the registry" in item for item in packet["boundaries"])


def test_packet_json_round_trip():
    data = frontier_garden.load_registry()
    packet = frontier_garden.build_packet(data, "FG-010", "FALSIFIER")
    encoded = json.dumps(packet, sort_keys=True)
    decoded = json.loads(encoded)
    assert decoded == packet


def test_authority_boundary_frontier_remains_non_authoritative():
    data = frontier_garden.load_registry()
    packet = frontier_garden.build_packet(data, "FG-020", "FALSIFIER")
    assert packet["standing"] == "INFORMATIVE_RESEARCH_ONLY"
    assert any("consequence-bearing permission" in item for item in packet["boundaries"])


def test_all_roles_can_build_packets():
    data = frontier_garden.load_registry()
    for role in frontier_garden.ROLES:
        packet = frontier_garden.build_packet(data, "FG-001", role)
        assert packet["role"] == role
        assert packet["role_instruction"]


def test_unknown_frontier_raises_key_error():
    data = frontier_garden.load_registry()
    try:
        frontier_garden.frontier_by_id(data, "FG-999")
    except KeyError as exc:
        assert exc.args == ("FG-999",)
    else:
        raise AssertionError("unknown frontier did not raise KeyError")


def test_every_frontier_has_searchable_lineage_header():
    data = frontier_garden.load_registry()
    allowed = {"speculative", "question", "evidence-backed"}
    for frontier in data["frontiers"]:
        header = frontier["lineage_header"]
        assert list(header) == ["origin", "parents", "status", "evidence_refs"]
        assert header["origin"]
        assert isinstance(header["parents"], list)
        assert header["status"] in allowed
        expected_refs = [
            source["path"] + ("#" + source["claim_or_test_id"] if source.get("claim_or_test_id") else "")
            for source in frontier["source_refs"]
        ]
        assert header["evidence_refs"] == expected_refs


def test_lineage_header_is_included_in_sterile_packet():
    data = frontier_garden.load_registry()
    packet = frontier_garden.build_packet(data, "FG-001", "FALSIFIER")
    assert packet["frontier"]["lineage_header"] == data["frontiers"][0]["lineage_header"]
