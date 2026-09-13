from __future__ import annotations

import argparse
import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

DIM = 8
NODES = 4
GLOBAL_SEED = 9062026


@dataclass(frozen=True)
class Event:
    name: str
    stimulus: tuple[float, ...]
    src: int
    dst: int
    gain: float = 1.0


@dataclass
class Agent:
    state: np.ndarray
    memory: np.ndarray
    relations: np.ndarray
    cumulative_change: float = 0.0
    transitions: int = 0

    def clone(self) -> "Agent":
        return Agent(
            state=self.state.copy(),
            memory=self.memory.copy(),
            relations=self.relations.copy(),
            cumulative_change=self.cumulative_change,
            transitions=self.transitions,
        )


def make_seed() -> Agent:
    rng = np.random.default_rng(GLOBAL_SEED)
    state = rng.normal(0.0, 0.05, size=DIM)
    memory = np.zeros(DIM)
    relations = np.zeros((NODES, NODES))
    return Agent(state=state, memory=memory, relations=relations)


def event_vector(index: int) -> tuple[float, ...]:
    rng = np.random.default_rng(1000 + index)
    vec = rng.normal(size=DIM)
    vec /= np.linalg.norm(vec) + 1e-12
    return tuple(float(x) for x in vec)


def base_events() -> list[Event]:
    return [
        Event(f"E{i}", event_vector(i), i % NODES, (i + 1) % NODES, 0.8 + 0.05 * i)
        for i in range(8)
    ]


def histories() -> dict[str, list[Event]]:
    events = base_events()
    repetitive = [events[0], events[1]] * 4
    variation = events[:]
    relational = [
        Event(e.name, e.stimulus, i % NODES, (i * 2 + 1) % NODES, e.gain)
        for i, e in enumerate(events)
    ]
    reordered = list(reversed(events))
    return {
        "A_repetition": repetitive,
        "B_variation": variation,
        "C_relational": relational,
        "D_reordered": reordered,
    }


def transition(agent: Agent, event: Event) -> float:
    before_state = agent.state.copy()
    before_memory = agent.memory.copy()
    before_rel = agent.relations.copy()

    x = np.asarray(event.stimulus, dtype=float)
    rel_signal = agent.relations[event.src, event.dst]
    history_term = 0.35 * agent.memory + 0.20 * rel_signal
    update = np.tanh(0.70 * x + history_term + 0.25 * agent.state)

    agent.state = np.tanh(0.82 * agent.state + event.gain * 0.22 * update)
    agent.memory = 0.88 * agent.memory + 0.12 * agent.state

    edge_delta = 0.10 * float(np.dot(agent.state, x))
    agent.relations[event.src, event.dst] = np.tanh(
        agent.relations[event.src, event.dst] + edge_delta
    )
    # small causal spread makes order matter without introducing randomness
    agent.relations[event.dst, :] *= 0.995

    delta = (
        np.linalg.norm(agent.state - before_state)
        + 0.5 * np.linalg.norm(agent.memory - before_memory)
        + 0.25 * np.linalg.norm(agent.relations - before_rel)
    )
    agent.cumulative_change += float(delta)
    agent.transitions += 1
    return float(delta)


def apply_history(seed: Agent, history: Iterable[Event]) -> Agent:
    agent = seed.clone()
    for event in history:
        transition(agent, event)
    return agent


def state_distance(a: Agent, b: Agent) -> float:
    return float(np.linalg.norm(a.state - b.state))


def relational_distance(a: Agent, b: Agent) -> float:
    return float(np.linalg.norm(a.relations - b.relations))


def composite_distance(a: Agent, b: Agent) -> float:
    return state_distance(a, b) + 0.5 * float(np.linalg.norm(a.memory - b.memory)) + 0.25 * relational_distance(a, b)


def probe_vector(index: int) -> np.ndarray:
    return np.asarray(event_vector(100 + index), dtype=float)


def behavior(agent: Agent, n: int = 16) -> np.ndarray:
    outputs = []
    for i in range(n):
        p = probe_vector(i)
        outputs.append(float(np.tanh(np.dot(agent.state + 0.5 * agent.memory, p))))
    return np.asarray(outputs)


def behavior_distance(a: Agent, b: Agent) -> float:
    return float(np.linalg.norm(behavior(a) - behavior(b)))


def reachability_signature(agent: Agent, n: int = 12) -> np.ndarray:
    sig = []
    for i in range(n):
        trial = agent.clone()
        p = tuple(float(x) for x in probe_vector(i))
        transition(trial, Event(f"P{i}", p, i % NODES, (i + 2) % NODES, 1.0))
        sig.extend(trial.state.tolist())
    return np.asarray(sig)


def reachability_distance(a: Agent, b: Agent) -> float:
    return float(np.linalg.norm(reachability_signature(a) - reachability_signature(b)))


def pairwise_metrics(agents: dict[str, Agent]) -> list[dict[str, float | str]]:
    names = sorted(agents)
    out = []
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            a, b = agents[left], agents[right]
            out.append(
                {
                    "left": left,
                    "right": right,
                    "state_distance": state_distance(a, b),
                    "relation_distance": relational_distance(a, b),
                    "behavior_distance": behavior_distance(a, b),
                    "reachability_distance": reachability_distance(a, b),
                    "composite_distance": composite_distance(a, b),
                }
            )
    return out


def crossover(agents: dict[str, Agent]) -> dict[str, Agent]:
    common = Event("COMMON_E", event_vector(999), 1, 3, 1.0)
    out = {}
    for name, agent in agents.items():
        nxt = agent.clone()
        transition(nxt, common)
        out[name] = nxt
    return out


def replay_test(seed: Agent, history: list[Event], original: Agent) -> dict[str, float]:
    replay = apply_history(seed, history)
    return {
        "state_distance": state_distance(original, replay),
        "relation_distance": relational_distance(original, replay),
        "behavior_distance": behavior_distance(original, replay),
    }


def ablation_map(seed: Agent, history: list[Event], reference: Agent) -> list[dict[str, float | int | str]]:
    result = []
    for i, event in enumerate(history):
        ablated = history[:i] + history[i + 1 :]
        agent = apply_history(seed, ablated)
        result.append(
            {
                "index": i,
                "event": event.name,
                "final_composite_delta_vs_reference": composite_distance(agent, reference),
                "behavior_delta_vs_reference": behavior_distance(agent, reference),
                "reachability_delta_vs_reference": reachability_distance(agent, reference),
            }
        )
    return result


def run() -> dict:
    seed = make_seed()
    hs = histories()
    agents = {name: apply_history(seed, history) for name, history in hs.items()}
    crossed = crossover(agents)

    replay = {
        name: replay_test(seed, hs[name], agents[name])
        for name in agents
    }

    ablations = {
        name: ablation_map(seed, hs[name], agents[name])
        for name in agents
    }

    seed_deltas = {
        name: {
            "state_distance_from_seed": state_distance(seed, agent),
            "relation_distance_from_seed": relational_distance(seed, agent),
            "behavior_distance_from_seed": behavior_distance(seed, agent),
            "reachability_distance_from_seed": reachability_distance(seed, agent),
            "cumulative_structural_change": agent.cumulative_change,
            "transition_count": agent.transitions,
        }
        for name, agent in agents.items()
    }

    crossover_effect = {
        name: {
            "same_event_transition_delta": composite_distance(agents[name], crossed[name]),
            "post_event_behavior_delta": behavior_distance(agents[name], crossed[name]),
        }
        for name in agents
    }

    report = {
        "experiment": "NURSERY-TIME-DIVERGENCE",
        "normative_ranking": None,
        "primary_variable": "divergence",
        "controls": {
            "byte_identical_seed": True,
            "deterministic_runtime": True,
            "history_length": {k: len(v) for k, v in hs.items()},
            "external_duration": "not simulated; transition count matched",
        },
        "seed_deltas": seed_deltas,
        "pairwise_pre_crossover": pairwise_metrics(agents),
        "pairwise_post_crossover": pairwise_metrics(crossed),
        "crossover_effect": crossover_effect,
        "replay": replay,
        "ablations": ablations,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("nursery_time_divergence_report.json"))
    args = parser.parse_args()
    report = run()
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "experiment": report["experiment"],
        "output": str(args.out),
        "pairwise_comparisons": len(report["pairwise_pre_crossover"]),
    }, indent=2))


if __name__ == "__main__":
    main()
