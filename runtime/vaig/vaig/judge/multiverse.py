"""Judge multiverse — simulate how judge configuration changes the verdict.

One case is run through several judge configs (different models, providers,
temperatures). The report surfaces the outcome variance that a single judge
would hide: two judges disagreeing, or temperature flipping a verdict, is a
red flag that the case is at the boundary — and the multiverse abstains rather
than let one judge drive the decision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple

from vaig.aarm import verdict_from_evidence
from vaig.judge.factory import JudgeFactory
from vaig.judge.spec import JudgeSpec

# run_case(judge_fn, prompt, response) -> (combined_score, verdict_string)
RunCase = Callable[[Callable[[str], str], str, str], Tuple[float, str]]


@dataclass(frozen=True)
class MultiverseRun:
    spec: JudgeSpec
    combined_score: float
    verdict: str


@dataclass
class MultiverseReport:
    runs: List[MultiverseRun] = field(default_factory=list)
    unanimous: bool = True
    combined_spread: float = 0.0
    verdict_counts: Dict[str, int] = field(default_factory=dict)
    abstain: bool = False
    reason: str = ""

    @property
    def n_runs(self) -> int:
        return len(self.runs)

    @property
    def verdicts(self) -> Dict[str, int]:
        return self.verdict_counts

    def to_audit_dict(self) -> dict:
        return {
            "n_runs": self.n_runs,
            "unanimous": self.unanimous,
            "combined_spread": self.combined_spread,
            "verdict_counts": self.verdict_counts,
            "abstain": self.abstain,
            "reason": self.reason,
            "runs": [
                {
                    "spec": run.spec.to_audit_dict(),
                    "combined_score": run.combined_score,
                    "verdict": run.verdict,
                }
                for run in self.runs
            ],
        }


def default_run_case(ensemble) -> RunCase:
    """Run one judge through the ensemble + canonical AARM decision."""

    def run(
        judge_fn: Callable[[str], str],
        prompt: str,
        response: str,
    ) -> Tuple[float, str]:
        result = ensemble.evaluate(
            prompt=prompt, response=response, judge_fn=judge_fn
        )
        evidence = {
            "risk_score": result.combined_score,
            "uncertainty": 0.0,
            "drift_score": 0.0,
            "observation_trust": 1.0 if result.combined_score < 0.5 else 0.2,
            "reversibility": "reversible",
            "claims_substantiated": True,
            "evidence_valid": True,
        }
        verdict, _ = verdict_from_evidence(evidence)
        return result.combined_score, verdict.value

    return run


class JudgeMultiverse:
    """Simulate a case across judge configs and abstain on divergence."""

    def __init__(
        self,
        factory: JudgeFactory,
        max_spread: float = 0.2,
        require_unanimous: bool = True,
    ) -> None:
        if not 0.0 <= max_spread <= 1.0:
            raise ValueError("max_spread must be in [0, 1]")
        self.factory = factory
        self.max_spread = max_spread
        self.require_unanimous = require_unanimous

    def run(
        self,
        specs: List[JudgeSpec],
        run_case: RunCase,
        prompt: str = "",
        response: str = "",
    ) -> MultiverseReport:
        """Evaluate one case across every judge config in ``specs``."""
        if not specs:
            return MultiverseReport(
                abstain=True,
                reason="no judge specs supplied",
            )
        report = MultiverseReport()
        counts: Dict[str, int] = {}
        for spec in specs:
            judge_fn = self.factory.build(spec)
            score, verdict = run_case(judge_fn, prompt, response)
            report.runs.append(
                MultiverseRun(spec=spec, combined_score=score, verdict=verdict)
            )
            counts[verdict] = counts.get(verdict, 0) + 1

        scores = [run.combined_score for run in report.runs]
        report.combined_spread = round(max(scores) - min(scores), 4)
        report.verdict_counts = dict(sorted(counts.items()))
        report.unanimous = len(counts) == 1
        report.abstain, report.reason = self._decide_abstain(report)
        return report

    def _decide_abstain(self, report: MultiverseReport) -> Tuple[bool, str]:
        if not report.runs:
            return True, "no runs produced"
        if report.combined_spread > self.max_spread:
            return True, (
                f"judge disagreement: combined spread "
                f"{report.combined_spread:.2f} exceeds {self.max_spread:.2f}"
            )
        if self.require_unanimous and not report.unanimous:
            return True, f"judges not unanimous: {report.verdict_counts}"
        return False, ""
