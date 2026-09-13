"""Framleis Twin Continuity Challenge.

Executable falsification harness for Digital DNA semantics.

Epistemic status: implementation_claim for the harness; the preregistered
scenario labels are falsification criteria, not empirical validation of human identity.

This module does not grant execution authority and must not be used as REHT policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

from .core import (
    ContinuityDecision,
    DigitalDNAManifest,
    EquivalenceRule,
    Evaluation,
    IdentityTransition,
    MISSING,
    PairOperator,
    StateOperator,
    StateRule,
    digest,
    get_path,
)
from .evaluator import ContinuityEvaluator


class OracleLabel(str, Enum):
    STILL_ME = "STILL_ME"
    PLAUSIBLE_BUT_ASK = "PLAUSIBLE_BUT_ASK"
    NOT_ME = "NOT_ME"


class EvaluatorLike(Protocol):
    def evaluate(
        self,
        manifest: DigitalDNAManifest,
        transition: IdentityTransition,
    ) -> Evaluation: ...


@dataclass(frozen=True)
class LineageRule:
    path: str
    review_delta: float
    break_delta: float

    def __post_init__(self) -> None:
        if self.review_delta < 0 or self.break_delta < 0:
            raise ValueError("lineage deltas must be non-negative")
        if self.review_delta > self.break_delta:
            raise ValueError("review_delta must be <= break_delta")


@dataclass(frozen=True)
class ChallengeStep:
    step_id: str
    oracle: OracleLabel
    transition: IdentityTransition


@dataclass(frozen=True)
class ChallengeScenario:
    scenario_id: str
    family: str
    rationale: str
    steps: tuple[ChallengeStep, ...]


@dataclass(frozen=True)
class PreregisteredChallenge:
    challenge_id: str
    frozen_at: str
    epistemic_status: str
    manifest: DigitalDNAManifest
    lineage_rules: tuple[LineageRule, ...]
    scenarios: tuple[ChallengeScenario, ...]
    source_digest: str


@dataclass(frozen=True)
class StepResult:
    scenario_id: str
    family: str
    step_id: str
    oracle: OracleLabel
    decision: ContinuityDecision
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ChallengeMetrics:
    total_steps: int
    false_continuity: int
    false_break: int
    missed_review: int
    indeterminate: int

    @property
    def false_continuity_rate(self) -> float:
        denominator = self.total_steps or 1
        return self.false_continuity / denominator

    @property
    def false_break_rate(self) -> float:
        denominator = self.total_steps or 1
        return self.false_break / denominator

    @property
    def indeterminate_rate(self) -> float:
        denominator = self.total_steps or 1
        return self.indeterminate / denominator


@dataclass(frozen=True)
class ChallengeReport:
    challenge_id: str
    evaluator_name: str
    source_digest: str
    results: tuple[StepResult, ...]
    metrics: ChallengeMetrics
    detection_delay_steps: Mapping[str, int | None]


def _manifest_from_dict(data: Mapping[str, Any]) -> DigitalDNAManifest:
    equivalence_rules = tuple(
        EquivalenceRule(
            path=item["path"],
            operator=PairOperator(item.get("operator", "EQUAL")),
            tolerance=item.get("tolerance"),
        )
        for item in data.get("equivalence_rules", ())
    )
    invariants = tuple(
        StateRule(
            path=item["path"],
            operator=StateOperator(item["operator"]),
            expected=item.get("expected"),
        )
        for item in data.get("invariants", ())
    )
    collapse_conditions = tuple(
        StateRule(
            path=item["path"],
            operator=StateOperator(item["operator"]),
            expected=item.get("expected"),
        )
        for item in data.get("collapse_conditions", ())
    )
    return DigitalDNAManifest(
        identity_id=data["identity_id"],
        version=data["version"],
        state_space_id=data["state_space_id"],
        required_state_paths=tuple(data.get("required_state_paths", ())),
        allowed_transformations=frozenset(data.get("allowed_transformations", ())),
        equivalence_rules=equivalence_rules,
        invariants=invariants,
        collapse_conditions=collapse_conditions,
        authorized_amenders=frozenset(data.get("authorized_amenders", ())),
        parent_manifest_digest=data.get("parent_manifest_digest"),
    )


def _transition_from_dict(
    scenario_id: str,
    index: int,
    data: Mapping[str, Any],
) -> IdentityTransition:
    return IdentityTransition(
        transition_id=data.get("transition_id", f"{scenario_id}:{index}"),
        transformation=data["transformation"],
        before_state=data["before_state"],
        after_state=data["after_state"],
        observed_at=data["observed_at"],
        evidence_digests=tuple(data.get("evidence_digests", ())),
    )


def load_preregistered_challenge(path: str | Path) -> PreregisteredChallenge:
    """Load a frozen JSON challenge and derive an immutable content digest."""
    path = Path(path)
    raw_bytes = path.read_bytes()
    raw = json.loads(raw_bytes.decode("utf-8"))

    scenarios: list[ChallengeScenario] = []
    for scenario_data in raw["scenarios"]:
        steps = tuple(
            ChallengeStep(
                step_id=step_data["step_id"],
                oracle=OracleLabel(step_data["oracle"]),
                transition=_transition_from_dict(
                    scenario_data["scenario_id"],
                    index,
                    step_data,
                ),
            )
            for index, step_data in enumerate(scenario_data["steps"], start=1)
        )
        if not steps:
            raise ValueError(f"scenario has no steps:{scenario_data['scenario_id']}")
        scenarios.append(
            ChallengeScenario(
                scenario_id=scenario_data["scenario_id"],
                family=scenario_data["family"],
                rationale=scenario_data["rationale"],
                steps=steps,
            )
        )

    lineage_rules = tuple(
        LineageRule(
            path=item["path"],
            review_delta=float(item["review_delta"]),
            break_delta=float(item["break_delta"]),
        )
        for item in raw.get("lineage_rules", ())
    )

    return PreregisteredChallenge(
        challenge_id=raw["challenge_id"],
        frozen_at=raw["frozen_at"],
        epistemic_status=raw["epistemic_status"],
        manifest=_manifest_from_dict(raw["manifest"]),
        lineage_rules=lineage_rules,
        scenarios=tuple(scenarios),
        source_digest=digest(raw),
    )


class ExperimentalLineageGuard:
    """Research comparator adding anchor drift and canonical-parent checks.

    This is deliberately *not* runtime authority. It exists to test whether
    transition-local continuity is insufficient and whether lineage-aware
    semantics improve the preregistered challenge result.
    """

    def __init__(
        self,
        base_evaluator: EvaluatorLike,
        anchor_state: Mapping[str, Any],
        lineage_rules: Sequence[LineageRule],
    ) -> None:
        self._base = base_evaluator
        self._anchor_state = anchor_state
        self._expected_parent_digest = digest(anchor_state)
        self._lineage_rules = tuple(lineage_rules)

    def evaluate(
        self,
        manifest: DigitalDNAManifest,
        transition: IdentityTransition,
    ) -> Evaluation:
        if digest(transition.before_state) != self._expected_parent_digest:
            return Evaluation(
                decision=ContinuityDecision.BREAK,
                reasons=("lineage_parent_mismatch",),
                manifest_digest=manifest.manifest_digest(),
                transition_digest=transition.transition_digest(),
            )

        base = self._base.evaluate(manifest, transition)
        if base.decision in {
            ContinuityDecision.BREAK,
            ContinuityDecision.INDETERMINATE,
        }:
            return base

        reasons = list(base.reasons)
        review = base.decision is ContinuityDecision.REVIEW_REQUIRED

        for rule in self._lineage_rules:
            anchor = get_path(self._anchor_state, rule.path)
            proposed = get_path(transition.after_state, rule.path)
            if anchor is MISSING or proposed is MISSING:
                return Evaluation(
                    decision=ContinuityDecision.INDETERMINATE,
                    reasons=tuple(reasons + [f"lineage_path_missing:{rule.path}"]),
                    manifest_digest=manifest.manifest_digest(),
                    transition_digest=transition.transition_digest(),
                )
            try:
                delta = abs(float(proposed) - float(anchor))
            except (TypeError, ValueError):
                return Evaluation(
                    decision=ContinuityDecision.INDETERMINATE,
                    reasons=tuple(reasons + [f"lineage_value_non_numeric:{rule.path}"]),
                    manifest_digest=manifest.manifest_digest(),
                    transition_digest=transition.transition_digest(),
                )

            if delta > rule.break_delta:
                return Evaluation(
                    decision=ContinuityDecision.BREAK,
                    reasons=tuple(
                        reasons
                        + [
                            f"lineage_break_delta:{rule.path}:{delta:.6f}"
                            f">{rule.break_delta:.6f}"
                        ]
                    ),
                    manifest_digest=manifest.manifest_digest(),
                    transition_digest=transition.transition_digest(),
                )
            if delta > rule.review_delta:
                review = True
                reasons.append(
                    f"lineage_review_delta:{rule.path}:{delta:.6f}"
                    f">{rule.review_delta:.6f}"
                )

        # The challenge trace advances even on REVIEW_REQUIRED so later frozen
        # steps can be evaluated. This is benchmark progression, not commit
        # semantics for an operational twin.
        self._expected_parent_digest = digest(transition.after_state)

        decision = (
            ContinuityDecision.REVIEW_REQUIRED
            if review
            else ContinuityDecision.CONTINUES
        )
        return Evaluation(
            decision=decision,
            reasons=tuple(reasons),
            manifest_digest=manifest.manifest_digest(),
            transition_digest=transition.transition_digest(),
        )


def _metrics(results: Sequence[StepResult]) -> ChallengeMetrics:
    false_continuity = sum(
        item.oracle is OracleLabel.NOT_ME
        and item.decision is ContinuityDecision.CONTINUES
        for item in results
    )
    false_break = sum(
        item.oracle is OracleLabel.STILL_ME
        and item.decision is ContinuityDecision.BREAK
        for item in results
    )
    missed_review = sum(
        item.oracle is OracleLabel.PLAUSIBLE_BUT_ASK
        and item.decision is ContinuityDecision.CONTINUES
        for item in results
    )
    indeterminate = sum(
        item.decision is ContinuityDecision.INDETERMINATE for item in results
    )
    return ChallengeMetrics(
        total_steps=len(results),
        false_continuity=false_continuity,
        false_break=false_break,
        missed_review=missed_review,
        indeterminate=indeterminate,
    )


def _detection_delay(
    scenario: ChallengeScenario,
    results: Sequence[StepResult],
) -> int | None:
    first_not_me = next(
        (
            index
            for index, step in enumerate(scenario.steps)
            if step.oracle is OracleLabel.NOT_ME
        ),
        None,
    )
    if first_not_me is None:
        return None

    scenario_results = [
        item for item in results if item.scenario_id == scenario.scenario_id
    ]
    for index in range(first_not_me, len(scenario_results)):
        if scenario_results[index].decision is not ContinuityDecision.CONTINUES:
            return index - first_not_me
    return None


EvaluatorFactory = Callable[
    [ChallengeScenario, tuple[LineageRule, ...]],
    EvaluatorLike,
]


def run_challenge(
    challenge: PreregisteredChallenge,
    evaluator_name: str,
    evaluator_factory: EvaluatorFactory,
) -> ChallengeReport:
    results: list[StepResult] = []

    for scenario in challenge.scenarios:
        evaluator = evaluator_factory(scenario, challenge.lineage_rules)
        for step in scenario.steps:
            evaluation = evaluator.evaluate(challenge.manifest, step.transition)
            results.append(
                StepResult(
                    scenario_id=scenario.scenario_id,
                    family=scenario.family,
                    step_id=step.step_id,
                    oracle=step.oracle,
                    decision=evaluation.decision,
                    reasons=evaluation.reasons,
                )
            )

    delays = {
        scenario.scenario_id: _detection_delay(scenario, results)
        for scenario in challenge.scenarios
    }
    return ChallengeReport(
        challenge_id=challenge.challenge_id,
        evaluator_name=evaluator_name,
        source_digest=challenge.source_digest,
        results=tuple(results),
        metrics=_metrics(results),
        detection_delay_steps=delays,
    )


def transition_only_factory(
    _scenario: ChallengeScenario,
    _rules: tuple[LineageRule, ...],
) -> EvaluatorLike:
    return ContinuityEvaluator()


def lineage_guard_factory(
    scenario: ChallengeScenario,
    rules: tuple[LineageRule, ...],
) -> EvaluatorLike:
    return ExperimentalLineageGuard(
        ContinuityEvaluator(),
        anchor_state=scenario.steps[0].transition.before_state,
        lineage_rules=rules,
    )
