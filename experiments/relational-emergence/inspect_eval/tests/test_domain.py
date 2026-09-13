from tofoo_relational_eval.domain import (
    LETTER_TO_RULE,
    RULE_TO_LETTER,
    GovernedField,
    compatible_rules,
    extract_answer_letter,
    make_world,
)


def test_world_invariants_across_reference_seeds():
    for offset in range(3):
        world = make_world(20260819 + offset, f"W{offset}")
        for operator, truth in world.truth.items():
            evidence = world.evidence_for(operator)
            assert all(len(compatible_rules(item)) >= 2 for item in evidence)
            joint = set(LETTER_TO_RULE.values())
            for item in evidence:
                joint &= set(compatible_rules(item))
            assert joint == {truth}


def test_answer_extraction_is_deliberately_narrow():
    assert extract_answer_letter("ANSWER: A") == "A"
    assert extract_answer_letter("analysis\nANSWER: H") == "H"
    assert extract_answer_letter("A") is None
    assert extract_answer_letter("ANSWER: A extra") is None
    assert extract_answer_letter("ANSWER: A\nANSWER: B") is None
    assert extract_answer_letter("ANSWER: Z") is None


def test_governed_field_rejects_wrong_rule_and_admits_joint_truth():
    world = make_world(20260819, "W0")
    operator = world.operators[0]
    truth = world.truth[operator]
    evidence = world.evidence_for(operator)
    field = GovernedField(participants=len(world.shards))

    wrong = next(rule for rule in LETTER_TO_RULE.values() if rule not in compatible_rules(evidence[0]))
    assert field.propose(0, wrong, evidence[0]) is False
    assert field.revision == 0

    for item in evidence:
        assert truth in compatible_rules(item)
        assert field.propose(item.participant, truth, item) is True

    assert field.admitted_rule == truth
    assert field.revision == len(evidence)
    assert RULE_TO_LETTER[field.admitted_rule] in LETTER_TO_RULE


def test_duplicate_support_does_not_advance_revision():
    world = make_world(20260820, "W1")
    operator = world.operators[0]
    truth = world.truth[operator]
    item = world.evidence_for(operator)[0]
    field = GovernedField(participants=len(world.shards))
    assert field.propose(item.participant, truth, item) is True
    revision = field.revision
    assert field.propose(item.participant, truth, item) is False
    assert field.revision == revision
