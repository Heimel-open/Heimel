"""Council data types."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class CouncilItem:
    id: str
    ts: float
    level: str               # "L3" or "L4"
    domain: str
    prompt_preview: str
    response_preview: str
    scores: Dict[str, float]
    verdict: Optional[str] = None       # "APPROVE" | "REJECT" | "OVERRIDE"
    verdict_ts: Optional[float] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_pending(self) -> bool:
        return self.verdict is None

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "ts": self.ts,
            "level": self.level,
            "domain": self.domain,
            "prompt_preview": self.prompt_preview,
            "response_preview": self.response_preview,
            "scores": self.scores,
            "verdict": self.verdict,
            "verdict_ts": self.verdict_ts,
            **self.meta,
        }
