"""
Human capability development for Relygon.

Relygon optimizes for increasing the person's ability to understand, choose,
and act independently. Assistance is therefore not monotonically increasing:
as demonstrated mastery rises, the system should shift from doing -> guiding ->
challenging -> observing, while preserving safety and governance constraints.

This module is intentionally separate from system autonomy maturity. A more
autonomous Relygon must not imply a less capable person.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class SupportMode(Enum):
    DO = "do"
    GUIDE = "guide"
    CHALLENGE = "challenge"
    OBSERVE = "observe"


@dataclass(frozen=True)
class CapabilityEvidence:
    capability: str
    demonstrated_mastery: float
    confidence: float = 1.0
    observations: int = 1

    def validated(self) -> "CapabilityEvidence":
        if not 0.0 <= self.demonstrated_mastery <= 1.0:
            raise ValueError("demonstrated_mastery must be between 0 and 1")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.observations < 1:
            raise ValueError("observations must be >= 1")
        return self


class CapabilityDevelopmentModel:
    """Tracks evidence-backed human mastery and selects the least substitutive help."""

    def __init__(self) -> None:
        self._capabilities: Dict[str, CapabilityEvidence] = {}

    def record(self, evidence: CapabilityEvidence) -> None:
        evidence.validated()
        current = self._capabilities.get(evidence.capability)
        if current is None or evidence.observations >= current.observations:
            self._capabilities[evidence.capability] = evidence

    def get(self, capability: str) -> Optional[CapabilityEvidence]:
        return self._capabilities.get(capability)

    def support_mode(
        self,
        capability: str,
        *,
        explicit_user_request: Optional[SupportMode] = None,
        urgency: bool = False,
        accessibility_need: bool = False,
        high_stakes: bool = False,
    ) -> SupportMode:
        if explicit_user_request is not None:
            return explicit_user_request
        if urgency or accessibility_need or high_stakes:
            return SupportMode.DO

        evidence = self._capabilities.get(capability)
        if evidence is None:
            return SupportMode.GUIDE

        score = evidence.demonstrated_mastery * evidence.confidence
        if evidence.observations < 2:
            return SupportMode.GUIDE
        if score < 0.45:
            return SupportMode.GUIDE
        if score < 0.75:
            return SupportMode.CHALLENGE
        return SupportMode.OBSERVE
