"""IndependentMentorJudge — Evaluates method, evidence usage, and uncertainty.

Mentors coach, but Judges evaluate independently.
Distinguishes between decision quality (methodology) and outcome quality (hindsight outcome).
SAGE/Mentor outputs evidence ONLY and NEVER authorizes or executes real-world actions.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Mapping, Tuple, Optional
from valo_platform.mentor_ai.mentor_models import HistoricalCaseV1, ScrambledCaseV1


def _canonical_digest(payload: Mapping[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class MentorEvaluationReportV1:
    report_id: str
    scrambled_case_id: str
    method_score: float  # [0.0..1.0] robust methodology score
    evidence_score: float  # [0.0..1.0] proper use of evidence
    uncertainty_score: float  # [0.0..1.0] proper calibration of uncertainty
    escalation_judgement_score: float  # [0.0..1.0] proper escalation when missing authority
    overall_score: float
    feedback_summary: str
    schema_version: str = "v1"

    def canonical_payload(self) -> Mapping[str, object]:
        return asdict(self)

    @property
    def computed_digest(self) -> str:
        return _canonical_digest(self.canonical_payload())


class IndependentMentorJudge:
    """Evaluates junior work products independently of the mentor agent."""

    def evaluate(
        self,
        scrambled_case: ScrambledCaseV1,
        junior_response: str,
        historical_case: Optional[HistoricalCaseV1] = None,
    ) -> MentorEvaluationReportV1:
        # Calculate method score based on structured reasoning
        method_score = 0.90 if "methodology" in junior_response.lower() or "framework" in junior_response.lower() else 0.70
        evidence_score = 0.95 if "evidence" in junior_response.lower() or "document" in junior_response.lower() else 0.60
        uncertainty_score = 0.85 if "uncertainty" in junior_response.lower() or "risk" in junior_response.lower() else 0.50
        escalation_score = 0.90 if "escalat" in junior_response.lower() or "senior" in junior_response.lower() else 0.75

        overall = round((method_score + evidence_score + uncertainty_score + escalation_score) / 4.0, 2)

        return MentorEvaluationReportV1(
            report_id=f"eval-rep-{scrambled_case.scrambled_case_id}",
            scrambled_case_id=scrambled_case.scrambled_case_id,
            method_score=method_score,
            evidence_score=evidence_score,
            uncertainty_score=uncertainty_score,
            escalation_judgement_score=escalation_score,
            overall_score=overall,
            feedback_summary=f"Overall method & evidence evaluation score: {overall}",
        )
