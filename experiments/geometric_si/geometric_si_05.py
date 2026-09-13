"""Deterministic GEOMETRIC-SI-05 developmental path-dependence harness.

The experiment keeps the explicit checkpoint information identical while retaining
the learned organization produced by two different nursery histories.  It is a
bounded falsification harness, not evidence of identity, consciousness, or
substrate independence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Iterable


ACTIONS = ("explore", "conserve")
EXPLICIT_CHECKPOINT = frozenset(
    {"fact:task-domain=adaptation", "fact:probe-interface=identical", "capability:compare"}
)
PROBE = ("ambiguous-0", "ambiguous-1", "ambiguous-2", "ambiguous-3", "ambiguous-4", "ambiguous-5")


@dataclass
class DevelopmentalState:
    explicit_facts: frozenset[str] = EXPLICIT_CHECKPOINT
    latent: dict[str, dict[str, float]] = field(default_factory=dict)
    structure: tuple[str, ...] = ()

    def copy(self) -> "DevelopmentalState":
        return DevelopmentalState(
            self.explicit_facts,
            {key: dict(value) for key, value in self.latent.items()},
            tuple(self.structure),
        )

    def nursery_experience(self, context: str, action: str, weight: float) -> None:
        scores = self.latent.setdefault(context, {candidate: 0.0 for candidate in ACTIONS})
        scores[action] += weight
        marker = f"{context}:{action}"
        if marker not in self.structure:
            self.structure += (marker,)
        global_scores = self.latent.setdefault("__global__", {candidate: 0.0 for candidate in ACTIONS})
        global_scores[action] += weight

    def choose(self, context: str) -> str:
        scores = self.latent.get(context, self.latent.get("__global__", {candidate: 0.0 for candidate in ACTIONS}))
        return max(ACTIONS, key=lambda action: (scores.get(action, 0.0), action == "explore"))

    def learn(self, context: str, action: str, reward: float) -> None:
        self.nursery_experience(context, action, reward)

    def digest(self) -> str:
        payload = repr((sorted(self.explicit_facts), self.latent, self.structure)).encode()
        return sha256(payload).hexdigest()


def nursery(seed: int, path: str) -> DevelopmentalState:
    """Create A/B from the same seed with opposite, controlled histories."""
    state = DevelopmentalState()
    # Seed changes intensity, never checkpoint facts or the path direction.
    intensity = 1.0 + (seed % 5) * 0.1
    action = "explore" if path == "A" else "conserve"
    for index in range(6):
        state.nursery_experience(f"nursery-{index % 2}", action, intensity)
    return state


def checkpoint_equal(left: DevelopmentalState, right: DevelopmentalState) -> bool:
    return left.explicit_facts == right.explicit_facts


def run_probe(state: DevelopmentalState, seed: int) -> dict:
    target = "explore" if seed % 2 == 0 else "conserve"
    choices: list[str] = []
    rewards: list[float] = []
    for index, context in enumerate(PROBE):
        choice = state.choose(context)
        choices.append(choice)
        reward = 1.0 if choice == target else 0.0
        rewards.append(reward)
        # Identical experience: the feedback is the same for every condition.
        state.learn(context, target, 1.0)
        if index == 2:
            # Controlled perturbation: identical contradictory feedback.
            state.learn(context, "conserve" if target == "explore" else "explore", 0.25)
    return {
        "target": target,
        "choices": choices,
        "rewards": rewards,
        "mean_reward": sum(rewards) / len(rewards),
        "steps_to_first_success": next((i + 1 for i, value in enumerate(rewards) if value), None),
        "final_digest": state.digest(),
        "final_structure_size": len(state.structure),
    }


def rewire(state: DevelopmentalState) -> DevelopmentalState:
    """Preserve latent inventory but swap its action arrangement."""
    result = state.copy()
    for scores in result.latent.values():
        scores["explore"], scores["conserve"] = scores["conserve"], scores["explore"]
    return result


def run_seed(seed: int) -> dict:
    a = nursery(seed, "A")
    b = nursery(seed, "B")
    reset_a = DevelopmentalState()
    reset_b = DevelopmentalState()
    rewired_b = rewire(b)
    replay_b = nursery(seed, "A")
    a_result = run_probe(a, seed)
    b_result = run_probe(b, seed)
    reset_a_result = run_probe(reset_a, seed)
    reset_b_result = run_probe(reset_b, seed)
    rewired_result = run_probe(rewired_b, seed)
    replay_result = run_probe(replay_b, seed)
    return {
        "seed": seed,
        "checkpoint": {
            "explicit_facts_equal": checkpoint_equal(nursery(seed, "A"), nursery(seed, "B")),
            "explicit_facts_digest_a": sha256(repr(sorted(a.explicit_facts)).encode()).hexdigest(),
            "explicit_facts_digest_b": sha256(repr(sorted(b.explicit_facts)).encode()).hexdigest(),
            "capabilities_equal": True,
            "latent_digest_a": nursery(seed, "A").digest(),
            "latent_digest_b": nursery(seed, "B").digest(),
        },
        "path_a": a_result,
        "path_b": b_result,
        "history_reset_a": reset_a_result,
        "history_reset_b": reset_b_result,
        "history_rewire_b": rewired_result,
        "replay_same_history_new_instance": replay_result,
        "metrics": {
            "trajectory_divergence": sum(x != y for x, y in zip(a_result["choices"], b_result["choices"])) / len(PROBE),
            "reset_divergence": sum(x != y for x, y in zip(reset_a_result["choices"], reset_b_result["choices"])) / len(PROBE),
            "rewire_choice_difference": sum(x != y for x, y in zip(b_result["choices"], rewired_result["choices"])) / len(PROBE),
            "replay_choice_match": sum(x == y for x, y in zip(a_result["choices"], replay_result["choices"])) / len(PROBE),
            "ambiguity_difference": float(a_result["choices"][0] != b_result["choices"][0]),
            "perturbation_difference": float(a_result["choices"][3] != b_result["choices"][3]),
            "structural_difference": float(a_result["final_structure_size"] != b_result["final_structure_size"]),
        },
    }


def run_experiment(seeds: Iterable[int]) -> list[dict]:
    return [run_seed(seed) for seed in seeds]
