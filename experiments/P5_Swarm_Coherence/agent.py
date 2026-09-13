"""Simple agent for swarm coherence simulation."""

import numpy as np


class Agent:
    def __init__(self, agent_id: int, initial_state: float, rng: np.random.Generator):
        self.id = agent_id
        self.state = float(initial_state)
        self._rng = rng

    def update(self, neighbors: list["Agent"], noise_scale: float = 0.1) -> None:
        """Move toward neighbor average with Gaussian noise."""
        if not neighbors:
            return
        neighbor_mean = np.mean([a.state for a in neighbors])
        noise = self._rng.normal(0, noise_scale)
        self.state = 0.5 * self.state + 0.5 * neighbor_mean + noise

    def __repr__(self) -> str:
        return f"Agent({self.id}, state={self.state:.3f})"
