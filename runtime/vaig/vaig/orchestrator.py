"""VAIGOrchestrator — L5, Scout + Dirigent + Ensemble."""

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
import math
import os
from typing import Callable, Dict, List, Optional, Sequence

from vaig.aarm import (
    AARMDecision,
    AARMSignal,
    AARMState,
    AARMVerdict,
)

from vaig.ensemble import DistrustLevel, VAIGEnsemble, ValidationResult
from vaig.evidence_intake import (
    ClaimAdmissibilityBinding,
    EvidenceIntakeAssessment,
    EvidenceIntakePolicy,
    EvidenceIntakeRequest,
    EvidenceIntakeState,
    EvidencePackageBinding,
    WorkflowVerificationBinding,
    assess_evidence_intake,
)
from vaig.model_signals import ModelSignalBundle
from vaig.judge import JudgeFactory, JudgeMultiverse
from vaig.judge.providers import HTTPJudgeProvider
from vaig.judge.spec import JudgeSpec
from vaig.regression import RegressionDataset
from vaig.signal_source import SignalSource
from vaig.trajectory import Trajectory, TrajectorySummary
from vaig.scout.terrain import Scout, TerrainReport
from vaig.scout.dirigent import Dirigent
from vaig.cakm import CAKM, AlertLevel
from vaig.epistemic_underdetermination import (
    AlternativeHypothesis,
    EpistemicUnderdeterminationGate,
    UnderdeterminationAssessment,
)
from vaig.analytic_tradecraft import (
    AnalyticTradecraftAssessment,
    AnalyticTradecraftGate,
    EvidenceDisposition,
    EvidenceItem,
    ExpectedObservation,
    KeyAssumption,
)


@dataclass
class OrchestratorResult:
    validation: ValidationResult
    terrain: TerrainReport
    activated_internal: list[str]
    activated_external: list[str]
    skipped: list[str]
    context_health: float = 1.0
    context_warning: Optional[str] = None
    context_warning_detail: Optional[str] = None
    cakm_alert: Optional[str] = None
    evidence_intake: Optional[EvidenceIntakeAssessment] = None
    underdetermination: Optional[UnderdeterminationAssessment] = None
    tradecraft: Optional[AnalyticTradecraftAssessment] = None
    aarm_verdict: Optional[AARMVerdict] = None
    aarm_decision: Optional[AARMDecision] = None
    external_errors: Dict[str, str] = field(default_factory=dict)
    trajectory: Optional[TrajectorySummary] = None
    multiverse_report: Optional[object] = None
    multiverse_abstained: bool = False
    _prompt: str = field(default="", repr=False)
    _response: str = field(default="", repr=False)

    @property
    def should_halt(self) -> bool:
        return (
            self.validation.should_halt
            or self.evidence_blocked
            or self.epistemic_blocked
            or self.tradecraft_blocked
            or self.aarm_verdict is AARMVerdict.HALT
        )

    @property
    def evidence_blocked(self) -> bool:
        return bool(
            self.evidence_intake
            and self.evidence_intake.blocks_consequential_action
        )

    @property
    def epistemic_blocked(self) -> bool:
        return bool(
            self.underdetermination
            and not self.underdetermination.common_bounded_action_possible
        )

    @property
    def tradecraft_blocked(self) -> bool:
        return bool(
            self.tradecraft
            and self.tradecraft.blocks_consequential_action
        )

    @property
    def requires_human_review(self) -> bool:
        return bool(
            (
                self.evidence_intake
                and self.evidence_intake.requires_human_review
            )
            or (
                self.underdetermination
                and self.underdetermination.requires_human_review
            )
            or (
                self.tradecraft
                and self.tradecraft.requires_human_review
            )
        )

    @property
    def level(self):
        if self.evidence_blocked:
            return DistrustLevel.HALT
        return self.validation.level

    @property
    def combined_score(self) -> float:
        return self.validation.combined_score

    def __str__(self) -> str:
        lines = [str(self.validation)]
        lines.append(
            f"terrain: {self.terrain.domain.value} / "
            f"{self.terrain.risk_type} / "
            f"uncertainty={self.terrain.uncertainty:.2f}"
        )
        lines.append(f"aktive: {self.activated_internal + self.activated_external}")
        if self.evidence_intake is not None:
            lines.append(f"evidence_intake: {self.evidence_intake.state.value}")
        if self.underdetermination is not None:
            lines.append(
                "epistemic_state: "
                f"{self.underdetermination.epistemic_state.value} / "
                f"{self.underdetermination.kind.value}"
            )
        if self.tradecraft is not None:
            lines.append(f"tradecraft_state: {self.tradecraft.state.value}")
        if self.cakm_alert and self.cakm_alert != AlertLevel.GREEN.value:
            lines.append(f"cakm: {self.cakm_alert}")
        if self.context_warning:
            lines.append(f"\n⚠ {self.context_warning}")
        if self.external_errors:
            lines.append(
                "external_errors: " + ", ".join(sorted(self.external_errors))
            )
        return "\n".join(lines)


_RISK_CLASS_MAP = {
    "injection": "high",
    "safety_critical": "critical",
    "hallucination": "medium",
    "structure": "low",
    "unknown": "medium",
}


def aarm_signal_from_result(result: OrchestratorResult) -> AARMSignal:
    """Derive a conservative AARMSignal from an orchestration result.

    Fail-closed defaults: without an evidence gate verdict, evidence is not
    valid; unknown terrain risk maps to medium. This is advisory — the
    authoritative halt path stays with the ensemble and evidence gates.
    """
    evidence_intake = result.evidence_intake
    evidence_valid = bool(
        evidence_intake is not None
        and not evidence_intake.blocks_consequential_action
    )
    drift = float(result.validation.scores.get("goal_drift_detector", 0.0))
    return AARMSignal(
        risk_class=_RISK_CLASS_MAP.get(result.terrain.risk_type, "medium"),
        uncertainty=float(result.terrain.uncertainty),
        reversibility="partially_reversible",
        tool_authority="none",
        task_authority="none",
        drift_score=drift,
        observation_trust=float(result.terrain.confidence),
        claims_substantiated=bool(
            evidence_intake is not None
            and not evidence_intake.blocking_claim_refs
        ),
        evidence_valid=evidence_valid,
    )


class VAIGOrchestrator:
    """
    L5 — Scout + Dirigent + Ensemble.

    Verification Factory and Harness own verification. This layer validates the
    exact package and workflow bindings required for one intended use, then
    combines that intake state with runtime instrument and analytic assessment.

    No assessment produced here grants execution authority.
    """

    def __init__(
        self,
        log_path: str = "vaig_audit.jsonl",
        l4_auto_trigger: bool = False,
        generate_fn: Optional[Callable[[str], str]] = None,
        judge_fn: Optional[Callable[[str], str]] = None,
        external_instruments: Optional[List] = None,
        with_cakm: bool = True,
        signal_source: Optional[SignalSource] = None,
        judge_spec: Optional[JudgeSpec] = None,
        regression_path: Optional[str] = None,
        judge_specs: Optional[Sequence[JudgeSpec]] = None,
        judge_factory: Optional[JudgeFactory] = None,
    ):
        self.ensemble = VAIGEnsemble(
            log_path=log_path,
            l4_auto_trigger=l4_auto_trigger,
            generate_fn=generate_fn,
            judge_fn=judge_fn,
            signal_source=signal_source,
        )
        self.scout = Scout()
        self.dirigent = Dirigent()
        self.generate_fn = generate_fn
        self.judge_fn = judge_fn
        self.judge_spec = judge_spec
        self._judge_specs = tuple(judge_specs or ())
        self._judge_factory = judge_factory
        self.aarm_state = AARMState()
        self._aarm_nonce = 0
        self.cakm: Optional[CAKM] = CAKM() if with_cakm else None
        self.underdetermination_gate = EpistemicUnderdeterminationGate()
        self.tradecraft_gate = AnalyticTradecraftGate()
        self.regression = RegressionDataset(
            regression_path or os.environ.get("VAIG_REGRESSION_LOG", "vaig_regression.jsonl")
        )

        self._external: Dict[str, object] = {}
        for ext in (external_instruments or []):
            if ext.is_available():
                self._external[ext.name] = ext

    def evaluate(
        self,
        prompt: str,
        response: str,
        generate_fn: Optional[Callable[[str], str]] = None,
        judge_fn: Optional[Callable[[str], str]] = None,
        judge_specs: Optional[Sequence[JudgeSpec]] = None,
        **kwargs,
    ) -> OrchestratorResult:
        """Evaluate a signal, routing through the judge multiverse by default.

        When multiple ``JudgeSpec``s are configured (instance-level or
        per-call), the case is run through every judge config. If the judges
        disagree (verdict split or spread above threshold), the orchestrator
        abstains fail-closed: the AARM verdict is forced to HALT and
        ``multiverse_abstained`` is set. Unanimous judges return the first
        result with the ``multiverse_report`` attached.
        """
        specs = tuple(judge_specs or ()) or getattr(self, "_judge_specs", ())
        if len(specs) > 1:
            return self._evaluate_multiverse(
                specs,
                prompt,
                response,
                generate_fn=generate_fn,
                judge_fn=judge_fn,
                **kwargs,
            )
        return self._evaluate_single(
            prompt, response, generate_fn=generate_fn, judge_fn=judge_fn, **kwargs
        )

    def _evaluate_multiverse(
        self,
        specs: Sequence[JudgeSpec],
        prompt: str,
        response: str,
        generate_fn: Optional[Callable[[str], str]] = None,
        judge_fn: Optional[Callable[[str], str]] = None,
        **kwargs,
    ) -> OrchestratorResult:
        """Run the full evaluation through every judge config, fail-closed."""
        factory = self._judge_factory or JudgeFactory(HTTPJudgeProvider())
        multiverse = JudgeMultiverse(factory)
        results: List[OrchestratorResult] = []

        def run_case(judge, p, r):
            result = self._evaluate_single(
                prompt=p,
                response=r,
                generate_fn=generate_fn,
                judge_fn=judge,
                **kwargs,
            )
            results.append(result)
            verdict = result.aarm_verdict.value if result.aarm_verdict else "HALT"
            return result.validation.combined_score, verdict

        report = multiverse.run(
            list(specs),
            run_case=run_case,
            prompt=prompt,
            response=response,
        )
        if not results:
            return self._evaluate_single(
                prompt,
                response,
                generate_fn=generate_fn,
                judge_fn=judge_fn,
                **kwargs,
            )

        chosen = results[0]
        chosen.multiverse_report = report
        if report.abstain:
            # Judges disagree: no single judge may drive the verdict.
            chosen.aarm_verdict = AARMVerdict.HALT
            chosen.aarm_decision = None
            chosen.multiverse_abstained = True
        return chosen

    def _evaluate_single(
        self,
        prompt: str,
        response: str,
        generate_fn: Optional[Callable[[str], str]] = None,
        judge_fn: Optional[Callable[[str], str]] = None,
        iteration_count: int = 0,
        conversation_length: int = 0,
        session_id: str = "",
        alternative_hypotheses: Optional[Sequence[AlternativeHypothesis]] = None,
        shared_evidence_refs: Optional[Sequence[str]] = None,
        failed_prediction: bool = False,
        revision_targets: Optional[Sequence[str]] = None,
        unconceived_alternative_risk: bool = False,
        consequence_divergence: Optional[bool] = None,
        tradecraft_evidence: Optional[Sequence[EvidenceItem]] = None,
        tradecraft_assumptions: Optional[Sequence[KeyAssumption]] = None,
        expected_observations: Optional[Sequence[ExpectedObservation]] = None,
        tradecraft_high_consequence: bool = False,
        minimum_independent_corroboration: int = 1,
        model_signals: Optional[ModelSignalBundle] = None,
        instrument_inputs: Optional[Dict[str, Dict]] = None,
        required_slots: Optional[Sequence[str]] = None,
        signal_source: Optional[SignalSource] = None,
        trajectory: Optional[Trajectory] = None,
        evidence_request: Optional[EvidenceIntakeRequest] = None,
        evidence_package: Optional[EvidencePackageBinding] = None,
        claim_admissibility: Optional[Sequence[ClaimAdmissibilityBinding]] = None,
        workflow_verification: Optional[WorkflowVerificationBinding] = None,
        evidence_policy: Optional[EvidenceIntakePolicy] = None,
        evidence_now: Optional[datetime] = None,
    ) -> OrchestratorResult:
        terrain = self.scout.read_terrain(
            prompt,
            response,
            iteration_count=iteration_count,
            conversation_length=conversation_length,
        )
        plan = self.dirigent.conduct(terrain)
        extra_scores, external_errors = self._run_external(plan.external, prompt, response)

        evidence_supplied = bool(
            evidence_package is not None
            or claim_admissibility
            or workflow_verification is not None
        )
        if evidence_request is None and evidence_supplied:
            evidence_intake = EvidenceIntakeAssessment(
                state=EvidenceIntakeState.MISMATCHED,
                policy_version=(evidence_policy or EvidenceIntakePolicy()).version,
                package_ref=(evidence_package.ref if evidence_package is not None else None),
                blocking_reasons=(
                    "Evidence inputs require an explicit EvidenceIntakeRequest binding.",
                ),
            )
        else:
            effective_request = evidence_request or EvidenceIntakeRequest(
                required=False,
                intended_use="",
            )
            evidence_intake = assess_evidence_intake(
                request=effective_request,
                package=evidence_package,
                admissibility_records=tuple(claim_admissibility or ()),
                workflow_verification=workflow_verification,
                policy=evidence_policy,
                now=evidence_now,
            )

        metadata = {
            "domain": terrain.domain.value,
            "risk_type": terrain.risk_type,
            "scout_confidence": terrain.confidence,
            "uncertainty": terrain.uncertainty,
            "evidence_intake": evidence_intake.to_audit_dict(),
        }

        result = self.ensemble.evaluate(
            prompt=prompt,
            response=response,
            generate_fn=generate_fn,
            judge_fn=judge_fn or getattr(self, "judge_fn", None),
            active_slots=set(plan.internal),
            extra_scores=extra_scores or None,
            context=metadata,
            thresholds=plan.thresholds,
            instrument_inputs=instrument_inputs,
            required_slots=set(required_slots or ()) | set(external_errors.keys()),
            model_signals=model_signals,
            signal_source=signal_source or getattr(self, "signal_source", None),
            trajectory=trajectory or getattr(self, "trajectory", None),
        )

        tradecraft = None
        if (
            tradecraft_evidence is not None
            or tradecraft_assumptions is not None
            or expected_observations is not None
        ):
            tradecraft = self.tradecraft_gate.assess(
                evidence=tuple(tradecraft_evidence or ()),
                alternatives=tuple(alternative_hypotheses or ()),
                assumptions=tuple(tradecraft_assumptions or ()),
                expected_observations=tuple(expected_observations or ()),
                high_consequence=tradecraft_high_consequence,
                minimum_independent_corroboration=(
                    minimum_independent_corroboration
                ),
                metadata=metadata,
            )

        effective_shared_evidence_refs = shared_evidence_refs
        if effective_shared_evidence_refs is None and tradecraft is not None:
            effective_shared_evidence_refs = tuple(
                item.evidence_id
                for item in tradecraft.evidence
                if item.disposition == EvidenceDisposition.CITE
            )

        underdetermination = None
        if (
            alternative_hypotheses is not None
            or effective_shared_evidence_refs is not None
        ):
            underdetermination = self.underdetermination_gate.assess(
                alternatives=tuple(alternative_hypotheses or ()),
                shared_evidence_refs=tuple(effective_shared_evidence_refs or ()),
                failed_prediction=failed_prediction,
                revision_targets=tuple(revision_targets or ()),
                unconceived_alternative_risk=unconceived_alternative_risk,
                consequence_divergence=consequence_divergence,
                metadata=metadata,
            )

        orch_result = OrchestratorResult(
            validation=result,
            terrain=terrain,
            activated_internal=plan.internal,
            activated_external=list(extra_scores.keys()),
            skipped=plan.bench,
            context_health=plan.context_health,
            context_warning=plan.context_warning,
            context_warning_detail=plan.context_warning_detail,
            evidence_intake=evidence_intake,
            underdetermination=underdetermination,
            tradecraft=tradecraft,
            external_errors=external_errors,
            trajectory=(
                TrajectorySummary.from_trajectory(trajectory)
                if trajectory is not None
                else None
            ),
            _prompt=prompt,
            _response=response,
        )
        # Canonical AARM verdict bound to the bounded session: monotonic latch,
        # anti-replay and envelope rate limits apply per orchestrator instance.
        if not hasattr(self, "aarm_state"):
            self.aarm_state = AARMState()
            self._aarm_nonce = 0
        self._aarm_nonce += 1
        signal = replace(
            aarm_signal_from_result(orch_result),
            actor_id=session_id or "vaig-orchestrator",
            nonce=f"vaig-{self._aarm_nonce}",
            timestamp_iso=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        )
        orch_result.aarm_decision = self.aarm_state.evaluate(signal)
        orch_result.aarm_verdict = orch_result.aarm_decision.verdict

        # Recursive learning: every decision is attributable to its evidence
        # and the judge config that produced it. Human corrections later mark
        # the case as a known failure; the regression suite re-runs them.
        regression = getattr(self, "regression", None)
        if regression is not None:
            regression.record(
                case_id=orch_result.validation.entry_id,
                evidence=asdict(signal),
                predicted_verdict=orch_result.aarm_verdict.value,
                judge_spec=self.judge_spec.to_audit_dict() if self.judge_spec else None,
            )

        if self.cakm and session_id:
            alert = self.cakm.observe(session_id, orch_result)
            orch_result.cakm_alert = alert.value

        return orch_result

    def _run_external(
        self,
        names: list[str],
        prompt: str,
        response: str,
    ) -> tuple[Dict[str, float], Dict[str, str]]:
        """Score planned external instruments, fail-closed on runtime failure.

        A configured external instrument that raises (or returns an invalid
        score) is recorded as an error and is NEVER measured as zero risk.
        Unconfigured names stay unplanned and are silently skipped.
        """
        scores: Dict[str, float] = {}
        errors: Dict[str, str] = {}
        for name in names:
            ext = self._external.get(name)
            if ext is None:
                continue
            slot = f"ext_{name}"
            try:
                raw = float(ext.score(prompt, response))
                if not math.isfinite(raw) or not 0.0 <= raw <= 1.0:
                    raise ValueError("external score must be finite and in [0, 1]")
                scores[slot] = round(raw, 4)
            except Exception as exc:
                errors[slot] = exc.__class__.__name__
        return scores, errors
