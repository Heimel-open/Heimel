"""
Exogenous Phi-Law filter (the Lawgiver).
Corrects agents that deviate beyond tolerance from the swarm median.
"""

import numpy as np
from typing import List
from agent import Agent


class PhiLawFilter:
    def __init__(self, tolerance: float = 0.3, correction_strength: float = 0.5):
        self.tolerance = tolerance
        self.correction_strength = correction_strength
        self.interventions: List[int] = []  # count per step

    def apply(self, agents: List[Agent]) -> int:
        """
        Correct deviating agents. Returns number of interventions this step.
        The filter is exogenous: it acts on agents from outside, not via peer influence.
        """
        median = np.median([a.state for a in agents])
        count = 0
        for agent in agents:
            deviation = abs(agent.state - median)
            if deviation > self.tolerance:
                agent.state += self.correction_strength * (median - agent.state)
                count += 1
        self.interventions.append(count)
        return count
