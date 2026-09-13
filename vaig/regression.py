"""Failure → regression dataset and suite for VAIG (samsara-loop adoption).

Every VAIG decision is attributable to the judge config that produced it.
When a human labels a decision wrong, the case enters the regression dataset
with its evidence, the recorded verdict, the corrected target, and the judge
spec — so a re-run of the current decision function can detect whether the
model/judge has regressed on known failures, or improved.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from vaig._version import __version__

# decide(evidence) -> verdict string (e.g. AARMVerdict.value)
DecisionFn = Callable[[Mapping[str, Any]], str]


@dataclass(frozen=True)
class RegressionCase:
    case_id: str
    evidence: Mapping[str, Any]
    predicted_verdict: str
    corrected_verdict: Optional[str]
    judge_spec: Optional[Mapping[str, Any]]
    recorded_at: str
    vaig_version: str


class RegressionDataset:
    """Append-only, versioned collection of decision cases (JSONL)."""

    def __init__(self, path: str | Path | None = None) -> None:
        self._cases: list[RegressionCase] = []
        self._path = Path(path) if path else None
        if self._path and self._path.exists():
            self.load(self._path)

    def record(
        self,
        *,
        case_id: str,
        evidence: Mapping[str, Any],
        predicted_verdict: str,
        corrected_verdict: Optional[str] = None,
        judge_spec: Optional[Mapping[str, Any]] = None,
    ) -> RegressionCase:
        case = RegressionCase(
            case_id=case_id,
            evidence=dict(evidence),
            predicted_verdict=predicted_verdict,
            corrected_verdict=corrected_verdict,
            judge_spec=dict(judge_spec) if judge_spec else None,
            recorded_at=datetime.now(timezone.utc).isoformat(),
            vaig_version=__version__,
        )
        self._cases.append(case)
        if self._path:
            self.persist(self._path)
        return case

    def cases(self) -> tuple[RegressionCase, ...]:
        return tuple(self._cases)

    def __len__(self) -> int:
        return len(self._cases)

    def find(self, case_id: str) -> Optional[RegressionCase]:
        return next((c for c in self._cases if c.case_id == case_id), None)

    def persist(self, path: str | Path | None = None) -> None:
        destination = Path(path) if path else self._path
        if not destination:
            return
        destination.parent.mkdir(parents=True, exist_ok=True)
        with open(destination, "w", encoding="utf-8") as fh:
            for case in self._cases:
                fh.write(json.dumps(asdict(case), ensure_ascii=False, sort_keys=True) + "\n")

    def load(self, path: str | Path) -> "RegressionDataset":
        self._path = Path(path)
        with open(self._path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                self._cases.append(
                    RegressionCase(
                        case_id=data["case_id"],
                        evidence=data["evidence"],
                        predicted_verdict=data["predicted_verdict"],
                        corrected_verdict=data.get("corrected_verdict"),
                        judge_spec=data.get("judge_spec"),
                        recorded_at=data["recorded_at"],
                        vaig_version=data.get("vaig_version", ""),
                    )
                )
        return self


@dataclass(frozen=True)
class RegressionReport:
    cases: int
    known_failures: int
    correct: int
    accuracy: float
    regression_rate: float
    regressions: tuple[str, ...]
    passed: bool


class RegressionSuite:
    """Re-run known failures against the current decision to detect regressions."""

    def __init__(self, dataset: RegressionDataset, min_accuracy: float = 0.85) -> None:
        self._dataset = dataset
        self._min_accuracy = min_accuracy

    def evaluate(self, decide: DecisionFn) -> RegressionReport:
        failures = [
            case for case in self._dataset.cases() if case.corrected_verdict is not None
        ]
        if not failures:
            return RegressionReport(
                cases=len(self._dataset),
                known_failures=0,
                correct=0,
                accuracy=1.0,
                regression_rate=0.0,
                regressions=(),
                passed=True,
            )
        regressions: list[str] = []
        correct = 0
        for case in failures:
            current = decide(case.evidence)
            if current == case.corrected_verdict:
                correct += 1
            else:
                regressions.append(
                    f"{case.case_id}: recorded={case.predicted_verdict} "
                    f"corrected={case.corrected_verdict} now={current}"
                )
        accuracy = correct / len(failures)
        return RegressionReport(
            cases=len(self._dataset),
            known_failures=len(failures),
            correct=correct,
            accuracy=round(accuracy, 4),
            regression_rate=round(1.0 - accuracy, 4),
            regressions=tuple(regressions),
            passed=accuracy >= self._min_accuracy,
        )
