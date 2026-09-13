from __future__ import annotations

import argparse
import hashlib
import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Owner:
    name: str
    cash: float
    risk_preference: float
    yield_received: float = 0.0
    portfolio: dict[str, float] = field(default_factory=dict)


@dataclass
class Agent:
    name: str
    domain: str
    skill: float
    cost: float
    reputation: float
    owner: str
    balance: float = 0.0
    completed_count: int = 0
    failure_count: int = 0


@dataclass
class Task:
    id: int
    domain: str
    reward: float
    risk: float
    required_skill: float
    authority_required: float


@dataclass
class Receipt:
    task_id: int
    agent: str
    owner: str
    decision: str
    quality: float
    payout: float
    owner_yield: float
    audit_hash: str


def stable_hash(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def create_market() -> tuple[dict[str, Owner], list[Agent]]:
    owners = {
        "Njal": Owner("Njal", cash=10000, risk_preference=0.62),
        "Triin": Owner("Triin", cash=5000, risk_preference=0.48),
        "InvestorA": Owner("InvestorA", cash=20000, risk_preference=0.72),
    }

    agents = [
        Agent("Analyst-01", "strategy", skill=0.82, cost=120, reputation=0.55, owner="Njal"),
        Agent("Builder-01", "code", skill=0.88, cost=160, reputation=0.60, owner="Njal"),
        Agent("Compliance-01", "governance", skill=0.78, cost=140, reputation=0.70, owner="Triin"),
        Agent("Sales-01", "sales", skill=0.70, cost=100, reputation=0.45, owner="InvestorA"),
        Agent("Research-01", "research", skill=0.90, cost=180, reputation=0.50, owner="InvestorA"),
    ]

    for agent in agents:
        owners[agent.owner].portfolio[agent.name] = 1.0

    return owners, agents


def generate_task(task_id: int) -> Task:
    domains = ["strategy", "code", "governance", "sales", "research"]
    return Task(
        id=task_id,
        domain=random.choice(domains),
        reward=random.randint(250, 1200),
        risk=random.random(),
        required_skill=random.uniform(0.45, 0.95),
        authority_required=random.uniform(0.2, 1.0),
    )


def valo_gate(agent: Agent, owner: Owner, task: Task) -> str:
    capability = (agent.skill * 0.65) + (agent.reputation * 0.35)

    if task.risk > 0.93 or task.authority_required > 0.95:
        return "HALT"
    if task.authority_required > owner.risk_preference + 0.25:
        return "DENY"
    if agent.reputation < 0.30 and task.risk > 0.45:
        return "DENY"
    if capability < task.required_skill:
        return "DENY"
    if task.risk > 0.66 or task.authority_required > owner.risk_preference:
        return "STEP_UP"
    return "ALLOW"


def score_quality(agent: Agent, task: Task, decision: str) -> float:
    base = (agent.skill * 0.68) + (agent.reputation * 0.32)
    risk_penalty = task.risk * 0.10
    review_boost = 0.04 if decision == "STEP_UP" else 0.0
    noise = random.uniform(-0.14, 0.14)
    return round(max(0.0, min(1.0, base - risk_penalty + review_boost + noise)), 3)


def select_agent(agents: list[Agent], task: Task) -> Agent | None:
    candidates = [agent for agent in agents if agent.domain == task.domain]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda agent: (agent.skill + agent.reputation) - (agent.cost / max(task.reward, 1)),
    )


def settle(agent: Agent, owner: Owner, task: Task, decision: str) -> Receipt:
    if decision in {"DENY", "HALT"}:
        quality = 0.0
        payout = 0.0
        owner_yield = 0.0
        if decision == "DENY":
            agent.reputation = max(0.0, agent.reputation - 0.01)
        payload = {
            "task_id": task.id,
            "agent": agent.name,
            "decision": decision,
            "payout": payout,
        }
        return Receipt(task.id, agent.name, agent.owner, decision, quality, payout, owner_yield, stable_hash(payload))

    quality = score_quality(agent, task, decision)
    review_cost = 50 if decision == "STEP_UP" else 0

    if quality >= 0.60:
        payout = round(max(0.0, (task.reward * quality) - agent.cost - review_cost), 2)
        owner_yield = round(payout * 0.60, 2)
        agent.balance = round(agent.balance + payout, 2)
        agent.completed_count += 1
        agent.reputation = round(min(1.0, agent.reputation + (0.025 * quality)), 3)
        owner.cash = round(owner.cash + owner_yield, 2)
        owner.yield_received = round(owner.yield_received + owner_yield, 2)
    else:
        payout = round(-(agent.cost * 0.25), 2)
        owner_yield = 0.0
        agent.balance = round(agent.balance + payout, 2)
        agent.failure_count += 1
        agent.reputation = round(max(0.0, agent.reputation - 0.05), 3)

    payload = {
        "task_id": task.id,
        "agent": agent.name,
        "decision": decision,
        "quality": quality,
        "payout": payout,
        "owner_yield": owner_yield,
    }
    return Receipt(task.id, agent.name, agent.owner, decision, quality, payout, owner_yield, stable_hash(payload))


def baro_signal(receipts: list[Receipt], agents: list[Agent]) -> dict:
    counts: dict[str, int] = {}
    for receipt in receipts:
        counts[receipt.decision] = counts.get(receipt.decision, 0) + 1

    total = max(len(receipts), 1)
    step_up_rate = counts.get("STEP_UP", 0) / total
    halt_rate = counts.get("HALT", 0) / total
    deny_rate = counts.get("DENY", 0) / total
    avg_reputation = sum(agent.reputation for agent in agents) / max(len(agents), 1)

    if halt_rate > 0.10 or deny_rate > 0.22:
        health = "unstable"
    elif step_up_rate > 0.35:
        health = "review-heavy"
    else:
        health = "operational"

    return {
        "schema_version": "baro.agent_market_signal.v1",
        "market_health": health,
        "decision_counts": counts,
        "step_up_rate": round(step_up_rate, 3),
        "deny_rate": round(deny_rate, 3),
        "halt_rate": round(halt_rate, 3),
        "avg_reputation": round(avg_reputation, 3),
    }


def simulate(rounds: int, seed: int) -> dict:
    random.seed(seed)
    owners, agents = create_market()
    receipts: list[Receipt] = []

    for task_id in range(1, rounds + 1):
        task = generate_task(task_id)
        agent = select_agent(agents, task)
        if agent is None:
            continue
        owner = owners[agent.owner]
        decision = valo_gate(agent, owner, task)
        receipts.append(settle(agent, owner, task, decision))

    return {
        "schema_version": "valo.agent_consultant_house.simulation.v1",
        "rounds": rounds,
        "seed": seed,
        "owners": {name: asdict(owner) for name, owner in owners.items()},
        "agents": [asdict(agent) for agent in agents],
        "receipts": [asdict(receipt) for receipt in receipts],
        "baro_signal": baro_signal(receipts, agents),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=80)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    result = simulate(rounds=args.rounds, seed=args.seed)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
