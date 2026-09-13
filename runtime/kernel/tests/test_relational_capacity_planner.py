import pytest

from valo_kernel.relational_capacity_planner import (
    AgentCandidate,
    Contribution,
    Dependency,
    GovernedRelation,
    PlanningError,
    RelationalContractError,
    SealedRelationalContract,
    TaskSpec,
    plan_relational_capacity,
    require_governed_relation,
    seal_relational_plan,
    verify_relational_contract,
)


def agent(agent_id, capabilities, peers=(), authority=()):
    return AgentCandidate(
        agent_id=agent_id,
        capabilities=frozenset(capabilities),
        permitted_peers=frozenset(peers),
        authority_scopes=frozenset(authority),
    )


def test_chooses_single_agent_when_one_can_do_entire_task():
    task = TaskSpec(
        task_id="reconcile",
        contributions=(
            Contribution("extract", "read_ledger"),
            Contribution("match", "reconcile"),
        ),
        dependencies=(Dependency("extract", "match"),),
    )
    plan = plan_relational_capacity(
        task,
        (
            agent("a", {"read_ledger", "reconcile"}),
            agent("b", {"read_ledger"}),
            agent("c", {"reconcile"}),
        ),
    )
    assert plan.selected_agents == ("a",)
    assert plan.relations == ()
    assert plan.dependency_depth == 2


def test_derives_only_required_governed_relation():
    task = TaskSpec(
        task_id="invoice",
        contributions=(
            Contribution("classify", "classify"),
            Contribution("approve", "approve", "invoice_approval"),
        ),
        dependencies=(Dependency("classify", "approve"),),
    )
    plan = plan_relational_capacity(
        task,
        (
            agent("classifier", {"classify"}, {"approver"}),
            agent("approver", {"approve"}, {"classifier"}, {"invoice_approval"}),
            agent("observer", {"classify", "approve"}),
        ),
    )
    assert plan.selected_agents == ("approver", "classifier")
    assert len(plan.relations) == 1
    assert plan.relations[0].source_agent == "classifier"
    assert plan.relations[0].target_agent == "approver"
    assert plan.relations[0].purpose == "classify->approve"


def test_finds_alternate_same_size_team_when_first_team_has_forbidden_relation():
    task = TaskSpec(
        task_id="alternate",
        contributions=(
            Contribution("left", "cap_left"),
            Contribution("right", "cap_right"),
        ),
        dependencies=(Dependency("left", "right"),),
    )
    plan = plan_relational_capacity(
        task,
        (
            agent("a_left", {"cap_left"}),
            agent("b_right_blocked", {"cap_right"}),
            agent("c_left", {"cap_left"}, {"d_right"}),
            agent("d_right", {"cap_right"}, {"c_left"}),
        ),
    )
    assert plan.selected_agents == ("c_left", "d_right")
    assert len(plan.relations) == 1
    assert plan.relations[0].source_agent == "c_left"
    assert plan.relations[0].target_agent == "d_right"


def test_does_not_invent_forbidden_coordination_edge():
    task = TaskSpec(
        task_id="blocked",
        contributions=(
            Contribution("a", "cap_a"),
            Contribution("b", "cap_b"),
        ),
        dependencies=(Dependency("a", "b"),),
    )
    with pytest.raises(PlanningError, match="no governed organization"):
        plan_relational_capacity(
            task,
            (
                agent("left", {"cap_a"}),
                agent("right", {"cap_b"}),
            ),
        )


def test_authority_is_part_of_eligibility():
    task = TaskSpec(
        task_id="pay",
        contributions=(Contribution("commit", "payment", "pay_10k"),),
    )
    plan = plan_relational_capacity(
        task,
        (
            agent("capable_only", {"payment"}),
            agent("authorized", {"payment"}, authority={"pay_10k"}),
        ),
    )
    assert plan.selected_agents == ("authorized",)


def test_rejects_dependency_depth_beyond_coordination_budget():
    task = TaskSpec(
        task_id="deep",
        contributions=tuple(Contribution(str(i), f"c{i}") for i in range(4)),
        dependencies=(
            Dependency("0", "1"),
            Dependency("1", "2"),
            Dependency("2", "3"),
        ),
        max_coordination_hops=2,
    )
    with pytest.raises(PlanningError, match="coordination budget"):
        plan_relational_capacity(
            task,
            (agent("all", {"c0", "c1", "c2", "c3"}),),
        )


def test_rejects_dependency_cycle():
    task = TaskSpec(
        task_id="cycle",
        contributions=(Contribution("a", "a"), Contribution("b", "b")),
        dependencies=(Dependency("a", "b"), Dependency("b", "a")),
    )
    with pytest.raises(PlanningError, match="acyclic"):
        plan_relational_capacity(task, (agent("all", {"a", "b"}),))


def test_seals_and_verifies_relational_contract_deterministically():
    task = TaskSpec(
        task_id="sealed",
        contributions=(Contribution("a", "a"), Contribution("b", "b")),
        dependencies=(Dependency("a", "b"),),
    )
    plan = plan_relational_capacity(
        task,
        (
            agent("left", {"a"}, {"right"}),
            agent("right", {"b"}, {"left"}),
        ),
    )
    first = seal_relational_plan(plan)
    second = seal_relational_plan(plan)
    assert first.contract_digest == second.contract_digest
    assert first.contract_digest == first.computed_digest
    assert verify_relational_contract(first)


def test_rejects_tampered_relational_contract():
    task = TaskSpec(
        task_id="tamper",
        contributions=(Contribution("a", "a"), Contribution("b", "b")),
        dependencies=(Dependency("a", "b"),),
    )
    plan = plan_relational_capacity(
        task,
        (
            agent("left", {"a"}, {"right"}),
            agent("right", {"b"}, {"left"}),
        ),
    )
    sealed = seal_relational_plan(plan)
    tampered = SealedRelationalContract(
        task_id=sealed.task_id,
        selected_agents=sealed.selected_agents,
        assignments=sealed.assignments,
        relations=(GovernedRelation("right", "left", "unexpected"),),
        dependency_depth=sealed.dependency_depth,
        contract_digest=sealed.contract_digest,
    )
    assert not verify_relational_contract(tampered)
    with pytest.raises(RelationalContractError, match="unsealed or tampered"):
        require_governed_relation(
            tampered,
            source_agent="right",
            target_agent="left",
            purpose="unexpected",
        )


def test_requires_exact_agent_pair_and_purpose_from_sealed_contract():
    task = TaskSpec(
        task_id="enforce",
        contributions=(Contribution("a", "a"), Contribution("b", "b")),
        dependencies=(Dependency("a", "b"),),
    )
    sealed = seal_relational_plan(
        plan_relational_capacity(
            task,
            (
                agent("left", {"a"}, {"right"}),
                agent("right", {"b"}, {"left"}),
            ),
        )
    )
    relation = require_governed_relation(
        sealed,
        source_agent="left",
        target_agent="right",
        purpose="a->b",
    )
    assert relation == GovernedRelation("left", "right", "a->b")

    with pytest.raises(RelationalContractError, match="not permitted"):
        require_governed_relation(
            sealed,
            source_agent="right",
            target_agent="left",
            purpose="b->a",
        )
