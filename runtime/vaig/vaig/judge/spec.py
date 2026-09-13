"""Judge configuration — which model + sampling config produced a verdict.

Every VAIG verdict that relies on a model judge must be attributable to an
exact judge configuration: provider, model id/version, temperature and token
budget. The config hash makes the outcome reproducible and lets the multiverse
simulate how different judge configs diverge.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

from vaig.digest import canonical_digest


@dataclass(frozen=True)
class JudgeSpec:
    """One exact judge configuration (model + sampling)."""

    provider: str
    model_id: str
    model_version: str
    temperature: float = 0.0
    max_tokens: int = 256
    provenance: str = "public"
    endpoint: Optional[str] = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("temperature must be in [0, 2]")
        if self.max_tokens < 1:
            raise ValueError("max_tokens must be at least 1")
        if self.provenance not in ("public", "private", "self-trained"):
            raise ValueError(f"unknown provenance: {self.provenance!r}")

    @property
    def config_hash(self) -> str:
        """Deterministic digest of the full judge configuration."""
        return canonical_digest(asdict(self))

    @property
    def stable_id(self) -> str:
        """Identity of the judge, ignoring sampling config."""
        return f"{self.provider}:{self.model_id}:{self.model_version}"

    def to_audit_dict(self) -> dict:
        payload = asdict(self)
        payload["config_hash"] = self.config_hash
        return payload
