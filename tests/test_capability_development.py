from paios.capability_development import (
    CapabilityDevelopmentModel,
    CapabilityEvidence,
    SupportMode,
)


def test_unknown_capability_guides():
    model = CapabilityDevelopmentModel()
    assert model.support_mode("budgeting") is SupportMode.GUIDE


def test_repeated_mastery_reduces_substitution():
    model = CapabilityDevelopmentModel()
    model.record(CapabilityEvidence("budgeting", demonstrated_mastery=0.8, confidence=0.95, observations=3))
    assert model.support_mode("budgeting") is SupportMode.OBSERVE


def test_partial_mastery_challenges():
    model = CapabilityDevelopmentModel()
    model.record(CapabilityEvidence("writing", demonstrated_mastery=0.65, confidence=0.9, observations=4))
    assert model.support_mode("writing") is SupportMode.CHALLENGE


def test_single_observation_never_withdraws_help():
    model = CapabilityDevelopmentModel()
    model.record(CapabilityEvidence("coding", demonstrated_mastery=1.0, confidence=1.0, observations=1))
    assert model.support_mode("coding") is SupportMode.GUIDE


def test_explicit_user_direction_overrides_developmental_default():
    model = CapabilityDevelopmentModel()
    model.record(CapabilityEvidence("tax", demonstrated_mastery=0.9, confidence=1.0, observations=5))
    assert model.support_mode("tax", explicit_user_request=SupportMode.DO) is SupportMode.DO


def test_high_stakes_defaults_to_do_not_withhold():
    model = CapabilityDevelopmentModel()
    model.record(CapabilityEvidence("medical-form", demonstrated_mastery=0.95, confidence=1.0, observations=5))
    assert model.support_mode("medical-form", high_stakes=True) is SupportMode.DO
