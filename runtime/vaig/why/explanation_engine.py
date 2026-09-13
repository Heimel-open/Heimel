"""
Explanation Engine — Post-hoc attribution for VALO decisions.

Generates human-readable explanations for why the system made a decision.
Each explanation is a channel: CAN (capability), SHOULD (policy), WHY (attribution).

This is a skeleton. AARM integration (SHOULD) and WORM read API (WHY)
are placeholders until future PRs provide those dependencies.
"""

from enum import Enum
from typing import Optional


class ExplanationChannel(str, Enum):
    can = "capability"
    should = "policy"
    why = "attribution"


class WhyGate:
    """
    Post-hoc attribution layer. Explains decisions, never influences them.

    Status: skeleton — not wired into ensemble.py or production paths.
    """

    def explain(self, decision) -> dict:
        """
        Generate explanation strings for each applicable channel.

        Args:
            decision: A DistrustDecision-like object with at minimum:
                      level (int), label (str), action (str), combined_score (float)

        Returns:
            dict mapping ExplanationChannel -> explanation string
        """
        level = getattr(decision, "level", 0)

        explanations = {}

        # CAN explains L0-L1 (CLEAR, WATCH)
        if level <= 1:
            explanations[ExplanationChannel.can] = self._can_explanation(decision)

        # SHOULD explains L2-L3 (FRICTION, COUNCIL)
        if 2 <= level <= 3:
            explanations[ExplanationChannel.should] = self._should_explanation(decision)
            # Also include CAN for context
            explanations[ExplanationChannel.can] = self._can_explanation(decision)

        # WHY explains all states, especially L4 (LOCK)
        if level >= 4 or level >= 2:
            explanations[ExplanationChannel.why] = self._why_explanation(decision)

        # If no specific channel matched, provide a generic explanation
        if not explanations:
            explanations[ExplanationChannel.can] = self._generic_explanation(decision)

        return explanations

    def _can_explanation(self, decision) -> str:
        """Explain based on capability — distrust level and confidence."""
        level = getattr(decision, "level", 0)
        label = getattr(decision, "label", "UNKNOWN")
        score = getattr(decision, "combined_score", 0.0)

        return (
            f"CAN: The system assessed this output as {label} (L{level}). "
            f"Combined confidence score: {score:.4f}. "
            f"This level is within the system's operational capability."
        )

    def _should_explanation(self, decision) -> str:
        """
        Explain based on policy — AARM governance context.

        Placeholder: AARM decision logging is not yet integrated.
        Returns a placeholder message indicating the policy reason
        will be available once AARM logging is complete.
        """
        level = getattr(decision, "level", 0)
        label = getattr(decision, "label", "UNKNOWN")

        return (
            f"SHOULD: This output triggered {label} (L{level}) due to policy. "
            f"AARM governance context will be available after PR #9 (wiring). "
            f"Current policy: require operator review for L{level} decisions."
        )

    def _why_explanation(self, decision) -> str:
        """
        Explain based on attribution — specific failure and WORM evidence.

        Placeholder: WORM read API is not yet built.
        Returns a placeholder message indicating detailed attribution
        will be available once the query layer provides WORM read access.
        """
        level = getattr(decision, "level", 0)
        label = getattr(decision, "label", "UNKNOWN")
        action = getattr(decision, "action", "UNKNOWN")

        return (
            f"WHY: Decision was {action} at level {label} (L{level}). "
            f"Specific instrument evidence will be available after query layer PR. "
            f"WORM log contains the full chain of evidence for this decision."
        )

    def _generic_explanation(self, decision) -> str:
        """Fallback for unexpected states."""
        label = getattr(decision, "label", "UNKNOWN")
        return f"System state: {label}. Explanation channels being determined."
