from dataclasses import dataclass, field
from typing import List


@dataclass
class TokenMeter:
    session_id: str
    language_inflation_factor: float = 1.0
    _turns: List[int] = field(default_factory=list, repr=False)

    def record_turn(self, tokens: int) -> None:
        self._turns.append(tokens)

    def n_turns(self) -> int:
        return len(self._turns)

    def rebilling_multiplier(self) -> float:
        """
        In a naive chat loop every turn resends the full conversation history.
        Total billed tokens = sum of cumulative history at each turn.
        Rebilling multiplier = total_billed / unique_tokens.

        For equal-length turns of n tokens over t turns:
            total_billed = n * (1 + 2 + ... + t) = n * t(t+1)/2
            unique_tokens = n * t
            multiplier    = (t+1)/2

        Example: 20 turns × 300 tokens → (20+1)/2 = 10.5x
        """
        if not self._turns:
            return 0.0
        unique_tokens = sum(self._turns)
        if unique_tokens == 0:
            return 0.0
        cumulative = 0
        total_billed = 0
        for t in self._turns:
            cumulative += t
            total_billed += cumulative
        return total_billed / unique_tokens

    def effective_tokens(self) -> float:
        """Unique tokens × rebilling multiplier × language inflation factor."""
        return sum(self._turns) * self.rebilling_multiplier() * self.language_inflation_factor
