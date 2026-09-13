import pytest

from src.valo_platform.advisor_fabric.profiles import (
    ADVISOR_PROFILES,
    get_advisor_profile,
    list_advisor_profiles,
)
from src.valo_platform.advisor_fabric.schemas import (
    AdvisorAuthorityBoundary,
    AdvisorMemoryPolicy,
    AdvisorRecommendationType,
)


EXPECTED_LEGACY_ADVISOR_ROLES = {
    "ceo",
    "cfo",
    "chro",
    "coo",
    "cto",
    "ciso",
    "procurement",
    "sustainability",
}


def test_registry_covers_legacy_advisor_roles_as_data() -> None:
    assert set(ADVISOR_PROFILES) == EXPECTED_LEGACY_ADVISOR_ROLES
    assert len(list_advisor_profiles()) == 8


def test_registered_profiles_are_advisory_only() -> None:
    for role, profile in ADVISOR_PROFILES.items():
        assert profile.role == role
        assert profile.advisor_id == f"advisor-{role}"
        assert profile.authority_boundary == AdvisorAuthorityBoundary.ADVISORY_ONLY
        assert profile.memory_policy == AdvisorMemoryPolicy.TENANT_SCOPED
        assert AdvisorRecommendationType.ACTION_CASE_DRAFT in profile.allowed_outputs
        assert "scout_signal" in profile.allowed_inputs
        assert "baro_evidence" in profile.allowed_inputs


def test_list_advisor_profiles_is_deterministic() -> None:
    roles = [profile.role for profile in list_advisor_profiles()]

    assert roles == sorted(EXPECTED_LEGACY_ADVISOR_ROLES)


def test_profile_registry_is_immutable() -> None:
    with pytest.raises(TypeError):
        ADVISOR_PROFILES["new-role"] = get_advisor_profile("ceo")  # type: ignore[index]


def test_unknown_profile_role_fails_closed() -> None:
    with pytest.raises(KeyError, match="unknown advisor role"):
        get_advisor_profile("olav")


def test_profiles_module_does_not_import_legacy_advisor_runtime() -> None:
    import src.valo_platform.advisor_fabric.profiles as profiles

    assert "valo_platform.advisors" not in profiles.__dict__
    assert "valo_platform.advisor" not in profiles.__dict__
