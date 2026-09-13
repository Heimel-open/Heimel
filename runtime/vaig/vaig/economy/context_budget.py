from dataclasses import dataclass


@dataclass
class ContextBudget:
    max_tokens: int = 100_000

    def is_over_budget(self, current_tokens: int) -> bool:
        return current_tokens > self.max_tokens

    def headroom(self, current_tokens: int) -> int:
        return max(0, self.max_tokens - current_tokens)

    def utilization(self, current_tokens: int) -> float:
        return current_tokens / self.max_tokens if self.max_tokens > 0 else 0.0
