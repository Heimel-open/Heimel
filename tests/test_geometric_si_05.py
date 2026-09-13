from experiments.geometric_si.geometric_si_05 import (
    EXPLICIT_CHECKPOINT,
    checkpoint_equal,
    nursery,
    rewire,
    run_seed,
)


def test_checkpoint_controls_explicit_information_but_not_latent_history():
    a = nursery(3, "A")
    b = nursery(3, "B")
    assert a.explicit_facts == b.explicit_facts == EXPLICIT_CHECKPOINT
    assert checkpoint_equal(a, b)
    assert a.digest() != b.digest()


def test_same_new_experience_diverges_after_different_nursery_paths():
    result = run_seed(0)
    assert result["metrics"]["trajectory_divergence"] > 0
    assert result["metrics"]["ambiguity_difference"] == 1.0


def test_history_reset_and_rewire_controls():
    result = run_seed(1)
    assert result["metrics"]["reset_divergence"] == 0.0
    assert result["metrics"]["rewire_choice_difference"] > 0


def test_replaying_history_in_new_instance_reproduces_trajectory():
    result = run_seed(7)
    assert result["metrics"]["replay_choice_match"] == 1.0


def test_rewire_preserves_inventory_but_changes_digest():
    original = nursery(2, "B")
    rewired = rewire(original)
    assert set(original.latent) == set(rewired.latent)
    assert original.digest() != rewired.digest()
