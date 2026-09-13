from pathlib import Path

from paios.node import RelAIonNode


def test_alpha_birth_is_persistent(tmp_path: Path) -> None:
    first = RelAIonNode(tmp_path, "Alpha")
    identity = first.identity

    second = RelAIonNode(tmp_path, "Alpha")
    assert second.identity == identity
    assert second.development.identity_root == identity.identity_root


def test_state_cannot_be_reopened_as_another_node(tmp_path: Path) -> None:
    RelAIonNode(tmp_path, "Alpha")

    try:
        RelAIonNode(tmp_path, "Beta")
    except ValueError as exc:
        assert "state belongs to node" in str(exc)
    else:
        raise AssertionError("node identity replacement must fail closed")


def test_health_requires_no_cloud_provider_for_continuity(tmp_path: Path) -> None:
    node = RelAIonNode(tmp_path, "Alpha")
    health = node.health()

    assert health["ok"] is True
    assert health["node"] == "Alpha"
    assert health["provider_required_for_continuity"] is False
    assert health["reht_required_for_effects"] is True


def test_identity_file_is_local_and_stable(tmp_path: Path) -> None:
    node = RelAIonNode(tmp_path, "Alpha")
    assert (tmp_path / "identity.json").exists()
    assert node.identity.identity_root.startswith("id-")
