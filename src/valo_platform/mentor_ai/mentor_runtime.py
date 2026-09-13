"""MentorAIRuntime — Socratic coaching runtime for junior knowledge workers.

Supported modes: observer-only, hint, guided, exam, reflection.
The mentor MUST NOT provide answers directly. It challenges assumptions, asks Socratic questions,
and requires explicit evidence justification.
SAGE/Mentor outputs evidence ONLY and NEVER authorizes or executes real-world actions.
"""
from enum import Enum
from typing import List, Optional
from valo_platform.mentor_ai.mentor_models import ScrambledCaseV1


class MentorMode(str, Enum):
    OBSERVER_ONLY = "observer_only"
    HINT = "hint"
    GUIDED = "guided"
    EXAM = "exam"
    REFLECTION = "reflection"


class MentorAIRuntime:
    """Socratic mentor coach runtime."""

    def __init__(self, mode: MentorMode = MentorMode.GUIDED) -> None:
        self.mode = mode

    def generate_feedback(self, scrambled_case: ScrambledCaseV1, junior_response: str) -> List[str]:
        prompts: List[str] = []

        if self.mode == MentorMode.OBSERVER_ONLY:
            return prompts

        # Socratic probing rules
        if "because" not in junior_response.lower() and "evidence" not in junior_response.lower():
            prompts.append("Socratic Challenge: What explicit evidence supports your conclusion?")

        if "100%" in junior_response or "certain" in junior_response.lower():
            prompts.append("Uncertainty Calibration: Have you identified potential risk factors or alternative hypotheses?")

        if self.mode == MentorMode.GUIDED:
            prompts.append("Guided Reflection: How does this case align with standard domain methodology?")

        if self.mode == MentorMode.HINT and len(prompts) == 0:
            prompts.append("Hint: Review the information asymmetry present in the initial scenario.")

        return prompts
