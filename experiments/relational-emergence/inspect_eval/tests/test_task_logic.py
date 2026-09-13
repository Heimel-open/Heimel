from tofoo_relational_eval.domain import RULE_NAMES, RULE_TO_LETTER
from tofoo_relational_eval.task import _multiple_choice_samples, _system_samples


def test_pooled_samples_have_stable_choices_and_targets():
    samples = _multiple_choice_samples(
        "pooled_raw", seed=20260819, worlds=1, participants=3, operators=3, rounds=3
    )
    assert len(samples) == 3
    for sample in samples:
        assert len(sample.choices) == len(RULE_NAMES)
        assert sample.target in RULE_TO_LETTER.values()
        assert len(sample.metadata["evidence"]) == 3


def test_isolated_expands_participants():
    samples = _multiple_choice_samples(
        "isolated", seed=20260819, worlds=1, participants=3, operators=3, rounds=3
    )
    assert len(samples) == 9
    assert all(len(sample.metadata["evidence"]) == 1 for sample in samples)


def test_system_conditions_have_one_sample_per_world_operator():
    samples = _system_samples(
        "relational_adaptive",
        seed=20260819,
        worlds=2,
        participants=3,
        operators=3,
        rounds=3,
    )
    assert len(samples) == 6
    assert all(len(sample.metadata["evidence"]) == 3 for sample in samples)
