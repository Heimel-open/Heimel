import pytest

from paios.development import (
    Ability,
    AbilityOrigin,
    DevelopmentState,
    Experience,
    MemoryState,
    RelationalCapability,
)


def exp(name: str, salience: float) -> Experience:
    return Experience(name, f"event:{name}", "observed consequence", salience, 1.0)


def test_forgetting_is_operative_not_evidence_deletion():
    alpha = DevelopmentState()
    alpha.experience(exp("noise", 0.10))
    report = alpha.sleep(decay=0.01, forget_below=0.15)
    assert report.forgotten == ("noise",)
    assert alpha.recall("noise") is None
    assert alpha.memories["noise"].event_ref == "event:noise"
    assert alpha.memories["noise"].state is MemoryState.DORMANT


def test_sleep_consolidates_salient_experience():
    alpha = DevelopmentState()
    alpha.experience(exp("important", 0.9))
    alpha.sleep()
    assert alpha.memories["important"].state is MemoryState.CONSOLIDATED


def test_borrowed_ability_requires_provider():
    with pytest.raises(ValueError):
        Ability("code", "skill:code", AbilityOrigin.BORROWED)


def test_practice_develops_proficiency_not_capability_ownership():
    ability = Ability("code", "skill:code", AbilityOrigin.BORROWED, provider_ref="model:external")
    alpha = DevelopmentState()
    alpha.register_ability(ability)
    alpha.practice("code", "event:p1", 1.0)
    assert ability.proficiency == pytest.approx(0.1)
    assert ability.provider_ref == "model:external"


def test_alpha_selects_learning_target_from_local_signal():
    alpha = DevelopmentState()
    assert alpha.choose_learning_target({"music": 0.2, "causality": 0.9}) == "causality"


def test_relational_capability_requires_evidence_and_kernel():
    with pytest.raises(ValueError):
        RelationalCapability("compose", (), "evidence:tada", 10.0)
    with pytest.raises(ValueError):
        RelationalCapability("compose", ("rel:a",), "", 10.0)


def test_capability_can_exist_before_detection():
    alpha = DevelopmentState()
    capability = RelationalCapability(
        "compose",
        ("rel:a", "rel:b"),
        "evidence:birth-certificate",
        realized_at=10.0,
    )
    alpha.register_relational_capability(capability)
    alpha.activate_relation("rel:a")
    assert not alpha.capability_realized("compose")
    alpha.activate_relation("rel:b")
    assert alpha.capability_realized("compose")
    assert not capability.detected
    alpha.mark_capability_detected("compose", 12.0)
    assert capability.detected
    assert capability.detected_at == 12.0


def test_kernel_deletion_removes_realization():
    alpha = DevelopmentState()
    alpha.register_relational_capability(
        RelationalCapability("compose", ("rel:a",), "evidence:birth-certificate", realized_at=10.0)
    )
    alpha.activate_relation("rel:a")
    assert alpha.capability_realized("compose")
    alpha.deactivate_relation("rel:a")
    assert not alpha.capability_realized("compose")


def test_detection_cannot_precede_realization():
    alpha = DevelopmentState()
    alpha.register_relational_capability(
        RelationalCapability("compose", ("rel:a",), "evidence:birth-certificate", realized_at=10.0)
    )
    with pytest.raises(ValueError):
        alpha.mark_capability_detected("compose", 9.0)


def test_development_has_no_authority_surface():
    alpha = DevelopmentState()
    assert not hasattr(alpha, "authority")
    assert not hasattr(alpha.self_model, "authority")
