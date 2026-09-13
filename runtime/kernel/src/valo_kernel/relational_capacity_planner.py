from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product
from typing import Iterable

from .contracts import canonical_digest


class PlanningError(ValueError):
    """Raised when no governed organization can satisfy the task."""


class RelationalContractError(ValueError):
    """Raised when a relational contract is invalid or a relation is not permitted."""


@dataclass(frozen=True)
class AgentCandidate:
    agent_id: str
    capabilities: frozenset[str]
    permitted_peers: frozenset[str]
    authority_scopes: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Contribution:
    contribution_id: str
    capability: str
    authority_scope: str | None = None


@dataclass(frozen=True)
class Dependency:
    upstream: str
    downstream: str


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    contributions: tuple[Contribution, ...]
    dependencies: tuple[Dependency, ...] = ()
    max_coordination_hops: int | None = None


@dataclass(frozen=True)
class Assignment:
    contribution_id: str
    agent_id: str


@dataclass(frozen=True)
class GovernedRelation:
    source_agent: str
    target_agent: str
    purpose: str


@dataclass(frozen=True)
class RelationalPlan:
    task_id: str
    assignments: tuple[Assignment, ...]
    relations: tuple[GovernedRelation, ...]
    selected_agents: tuple[str, ...]
    dependency_depth: int


@dataclass(frozen=True)
class SealedRelationalContract:
    task_id: str
    selected_agents: tuple[str, ...]
    assignments: tuple[Assignment, ...]
    relations: tuple[GovernedRelation, ...]
    dependency_depth: int
    contract_digest: str

    def canonical_payload(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "selected_agents": self.selected_agents,
            "assignments": tuple(
                {
                    "contribution_id": item.contribution_id,
                    "agent_id": item.agent_id,
                }
                for item in self.assignments
            ),
            "relations": tuple(
                {
                    "source_agent": item.source_agent,
                    "target_agent": item.target_agent,
                    "purpose": item.purpose,
                }
                for item in self.relations
            ),
            "dependency_depth": self.dependency_depth,
        }

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())


def _validate_task(task: TaskSpec) -> None:
    ids = [item.contribution_id for item in task.contributions]
    if not ids:
        raise PlanningError("task requires at least one contribution")
    if len(ids) != len(set(ids)):
        raise PlanningError("contribution ids must be unique")
    known = set(ids)
    for dep in task.dependencies:
        if dep.upstream not in known or dep.downstream not in known:
            raise PlanningError("dependency references unknown contribution")
        if dep.upstream == dep.downstream:
            raise PlanningError("self dependency is not allowed")


def _dependency_depth(task: TaskSpec) -> int:
    children: dict[str, list[str]] = {c.contribution_id: [] for c in task.contributions}
    indegree: dict[str, int] = {c.contribution_id: 0 for c in task.contributions}
    for dep in task.dependencies:
        children[dep.upstream].append(dep.downstream)
        indegree[dep.downstream] += 1

    depth = {node: 1 for node in indegree}
    queue = sorted(node for node, degree in indegree.items() if degree == 0)
    visited = 0
    while queue:
        node = queue.pop(0)
        visited += 1
        for child in sorted(children[node]):
            depth[child] = max(depth[child], depth[node] + 1)
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
                queue.sort()
    if visited != len(indegree):
        raise PlanningError("dependency graph must be acyclic")
    return max(depth.values(), default=0)


def _eligible(agent: AgentCandidate, contribution: Contribution) -> bool:
    if contribution.capability not in agent.capabilities:
        return False
    if contribution.authority_scope is not None and contribution.authority_scope not in agent.authority_scopes:
        return False
    return True


def _relations(
    task: TaskSpec,
    assignments: tuple[Assignment, ...],
    agents: dict[str, AgentCandidate],
) -> tuple[GovernedRelation, ...] | None:
    owner = {item.contribution_id: item.agent_id for item in assignments}
    relations: set[GovernedRelation] = set()
    for dep in task.dependencies:
        source = owner[dep.upstream]
        target = owner[dep.downstream]
        if source == target:
            continue
        if target not in agents[source].permitted_peers or source not in agents[target].permitted_peers:
            return None
        relations.add(
            GovernedRelation(
                source_agent=source,
                target_agent=target,
                purpose=f"{dep.upstream}->{dep.downstream}",
            )
        )
    return tuple(sorted(relations, key=lambda item: (item.source_agent, item.target_agent, item.purpose)))


def _find_minimum_plan(
    task: TaskSpec,
    agents_tuple: tuple[AgentCandidate, ...],
) -> tuple[tuple[str, ...], tuple[Assignment, ...], tuple[GovernedRelation, ...]]:
    by_agent = {agent.agent_id: agent for agent in agents_tuple}
    contributions = tuple(sorted(task.contributions, key=lambda item: item.contribution_id))
    agent_ids = tuple(agent.agent_id for agent in agents_tuple)

    for size in range(1, len(agent_ids) + 1):
        for selected in combinations(agent_ids, size):
            choices: list[tuple[str, ...]] = []
            feasible = True
            for contribution in contributions:
                eligible = tuple(
                    agent_id
                    for agent_id in selected
                    if _eligible(by_agent[agent_id], contribution)
                )
                if not eligible:
                    feasible = False
                    break
                choices.append(eligible)
            if not feasible:
                continue

            for assignment_choice in product(*choices):
                assignments = tuple(
                    Assignment(contribution.contribution_id, agent_id)
                    for contribution, agent_id in zip(contributions, assignment_choice)
                )
                relations = _relations(task, assignments, by_agent)
                if relations is None:
                    continue
                used = tuple(sorted({item.agent_id for item in assignments}))
                if len(used) != size:
                    continue
                return used, assignments, relations

    raise PlanningError("no governed organization can satisfy task")


def plan_relational_capacity(task: TaskSpec, candidates: Iterable[AgentCandidate]) -> RelationalPlan:
    """Return the minimum deterministic governed organization for a bounded candidate set."""

    _validate_task(task)
    agents_tuple = tuple(sorted(candidates, key=lambda item: item.agent_id))
    ids = [agent.agent_id for agent in agents_tuple]
    if not agents_tuple:
        raise PlanningError("candidate set cannot be empty")
    if len(ids) != len(set(ids)):
        raise PlanningError("agent ids must be unique")

    depth = _dependency_depth(task)
    if task.max_coordination_hops is not None and depth - 1 > task.max_coordination_hops:
        raise PlanningError("task dependency depth exceeds coordination budget")

    selected, assignments, relations = _find_minimum_plan(task, agents_tuple)
    return RelationalPlan(
        task_id=task.task_id,
        assignments=assignments,
        relations=relations,
        selected_agents=selected,
        dependency_depth=depth,
    )


def seal_relational_plan(plan: RelationalPlan) -> SealedRelationalContract:
    """Seal a planner result into a deterministic, tamper-evident relational contract."""

    provisional = SealedRelationalContract(
        task_id=plan.task_id,
        selected_agents=tuple(sorted(plan.selected_agents)),
        assignments=tuple(
            sorted(plan.assignments, key=lambda item: (item.contribution_id, item.agent_id))
        ),
        relations=tuple(
            sorted(
                plan.relations,
                key=lambda item: (item.source_agent, item.target_agent, item.purpose),
            )
        ),
        dependency_depth=plan.dependency_depth,
        contract_digest="",
    )
    return SealedRelationalContract(
        task_id=provisional.task_id,
        selected_agents=provisional.selected_agents,
        assignments=provisional.assignments,
        relations=provisional.relations,
        dependency_depth=provisional.dependency_depth,
        contract_digest=provisional.computed_digest,
    )


def verify_relational_contract(contract: SealedRelationalContract) -> bool:
    """Return True only for a structurally valid, untampered contract."""

    if not contract.contract_digest or contract.contract_digest != contract.computed_digest:
        return False
    selected = set(contract.selected_agents)
    if not selected or len(selected) != len(contract.selected_agents):
        return False
    if any(item.agent_id not in selected for item in contract.assignments):
        return False
    if any(
        item.source_agent not in selected or item.target_agent not in selected
        for item in contract.relations
    ):
        return False
    return True


def require_governed_relation(
    contract: SealedRelationalContract,
    *,
    source_agent: str,
    target_agent: str,
    purpose: str,
) -> GovernedRelation:
    """Fail closed unless an exact communication relation is present in the sealed contract."""

    if not verify_relational_contract(contract):
        raise RelationalContractError("relational contract is unsealed or tampered")
    if source_agent not in contract.selected_agents or target_agent not in contract.selected_agents:
        raise RelationalContractError("agent is outside sealed relational organization")
    expected = GovernedRelation(source_agent, target_agent, purpose)
    if expected not in contract.relations:
        raise RelationalContractError("relation is not permitted by sealed relational contract")
    return expected
