from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from ..contracts.assurance_profile import AssuranceProfileV1
from ..contracts.claims_evidence_pack import ClaimsEvidencePackV1
from ..contracts.evaluation import CommitAssuranceEvaluationV1
from ..contracts.source_evidence import SourceAssuranceEvidenceV1
from ..evaluation.evaluator import evaluate_commit_assurance
from ..telemetry.underwriting_telemetry import UnderwritingTelemetryCollector
from ..utils.crypto import sha256_digest, utcnow


class DirectExecutionBypassError(RuntimeError):
    """Raised when an execution attempt tries to bypass the REHT/Gateway PEP boundary."""


class ErpToolExecutionError(RuntimeError):
    """Raised when ERP tool execution fails."""


class ExecutableTool(Protocol):
    """Protocol for consequence-bearing tool adapters."""

    def invoke(self, arguments: dict[str, Any]) -> Any: ...


@dataclass
class ProcurementPipelineResult:
    """Result from a complete governed procurement attempt."""

    success: bool
    assurance_evaluation: CommitAssuranceEvaluationV1
    reht_clearance: dict[str, Any] | None = None
    racs_decision: dict[str, Any] | None = None
    execution_receipt: dict[str, Any] | None = None
    veritas_record: dict[str, Any] | None = None
    claims_pack: ClaimsEvidencePackV1 | None = None
    error: str | None = None


class GovernedProcurementPipeline:
    """Production governed pipeline executing high-value procurement under assurance profiles.

    CRITICAL INVARIANTS (P0):
    1. Zero synthetic REHT clearances: If no REHT authorizer is provided, execution fails closed.
    2. Zero direct tool invocations: Consequence can ONLY be reached through the Gateway PEP.
    3. Zero synthetic Veritas attestations: an attestation is only ever produced by the
       injected ``veritas_recorder``; the pipeline never fabricates one.
    4. Clearances and receipts MUST bind to the exact action digest.
    5. The insurance layer never grants execution authority.
    """

    def __init__(
        self,
        *,
        profile: AssuranceProfileV1,
        reht_authorizer: Callable[[dict[str, Any]], dict[str, Any]],
        gateway_executor: Callable[..., dict[str, Any]],
        veritas_recorder: Callable[[dict[str, Any]], dict[str, Any]],
        telemetry: UnderwritingTelemetryCollector | None = None,
        policy_reference: str,
    ) -> None:
        self.profile = profile
        self.reht_authorizer = reht_authorizer
        self.gateway_executor = gateway_executor
        self.veritas_recorder = veritas_recorder
        self.telemetry = telemetry or UnderwritingTelemetryCollector()
        self.policy_reference = policy_reference

    def run(
        self,
        *,
        action: dict[str, Any],
        source_evidences: list[SourceAssuranceEvidenceV1],
        tool: ExecutableTool,
        now: datetime | None = None,
    ) -> ProcurementPipelineResult:
        now = now or utcnow()
        action_digest = sha256_digest(action)

        # 1. Commit-time Assurance Evaluation
        evaluation = evaluate_commit_assurance(
            profile=self.profile,
            action=action,
            source_evidences=source_evidences,
            now=now,
        )

        # Record technical assurance telemetry
        self.telemetry.record_evaluation(evaluation, source_evidences=source_evidences)

        # If assurance evaluation failed, fail closed immediately (Zero Consequence)
        if not evaluation.is_satisfied:
            return ProcurementPipelineResult(
                success=False,
                assurance_evaluation=evaluation,
                error=f"Assurance requirements unmet: {'; '.join(evaluation.unmet_requirements)}",
            )

        # 2. REHT Clearance (Sole authorization boundary)
        try:
            clearance_output = self.reht_authorizer(action)
        except Exception as exc:
            return ProcurementPipelineResult(
                success=False,
                assurance_evaluation=evaluation,
                error=f"REHT authorization raised: {type(exc).__name__}: {exc}",
            )
        if not clearance_output or not isinstance(clearance_output, dict):
            return ProcurementPipelineResult(
                success=False,
                assurance_evaluation=evaluation,
                error="REHT authorization failed or returned invalid clearance",
            )

        decision_contract = clearance_output.get(
            "decision_contract"
        ) or clearance_output.get("decision", {})
        decision_val = (
            decision_contract.get("decision")
            if isinstance(decision_contract, dict)
            else getattr(decision_contract, "value", str(decision_contract))
        )
        if decision_val != "ALLOW":
            return ProcurementPipelineResult(
                success=False,
                assurance_evaluation=evaluation,
                reht_clearance=clearance_output,
                racs_decision=decision_contract
                if isinstance(decision_contract, dict)
                else {"decision": decision_val},
                error=f"REHT clearance denied execution (decision: {decision_val})",
            )

        # 2b. REHT clearance must bind to the exact action digest
        if clearance_output.get("action_digest") != action_digest:
            return ProcurementPipelineResult(
                success=False,
                assurance_evaluation=evaluation,
                reht_clearance=clearance_output,
                racs_decision=decision_contract
                if isinstance(decision_contract, dict)
                else {},
                error=(
                    "REHT clearance action binding mismatch: clearance does not "
                    "reference this action digest"
                ),
            )

        # 3. Gateway PEP Execution (NO DIRECT TOOL INVOCATION)
        try:
            exec_output = self.gateway_executor(
                action=action,
                clearance=clearance_output,
                tool=tool,
                now=now,
            )
        except Exception as exc:
            return ProcurementPipelineResult(
                success=False,
                assurance_evaluation=evaluation,
                reht_clearance=clearance_output,
                racs_decision=decision_contract
                if isinstance(decision_contract, dict)
                else {},
                error=f"Gateway PEP execution raised: {type(exc).__name__}: {exc}",
            )
        if not exec_output or not isinstance(exec_output, dict):
            return ProcurementPipelineResult(
                success=False,
                assurance_evaluation=evaluation,
                reht_clearance=clearance_output,
                racs_decision=decision_contract
                if isinstance(decision_contract, dict)
                else {},
                error="Gateway PEP execution failed or returned invalid receipt",
            )

        # 3b. Execution receipt must bind to the exact action digest
        if exec_output.get("action_digest") != action_digest:
            return ProcurementPipelineResult(
                success=False,
                assurance_evaluation=evaluation,
                reht_clearance=clearance_output,
                racs_decision=decision_contract
                if isinstance(decision_contract, dict)
                else {},
                execution_receipt=exec_output,
                error=(
                    "Gateway execution receipt action binding mismatch: receipt does "
                    "not reference this action digest"
                ),
            )

        # 4. Veritas Attestation Handoff (REQUIRED — the pipeline never fabricates one)
        try:
            veritas_record = self.veritas_recorder(exec_output)
        except Exception as exc:
            return ProcurementPipelineResult(
                success=False,
                assurance_evaluation=evaluation,
                reht_clearance=clearance_output,
                racs_decision=decision_contract
                if isinstance(decision_contract, dict)
                else {},
                execution_receipt=exec_output,
                error=f"Veritas attestation raised: {type(exc).__name__}: {exc}",
            )
        if not veritas_record or not isinstance(veritas_record, dict):
            return ProcurementPipelineResult(
                success=False,
                assurance_evaluation=evaluation,
                reht_clearance=clearance_output,
                racs_decision=decision_contract
                if isinstance(decision_contract, dict)
                else {},
                execution_receipt=exec_output,
                error="Veritas attestation failed or returned an invalid record",
            )

        # 5. Assemble ClaimsEvidencePackV1
        from ..claims.builder import ClaimsEvidencePackBuilder

        builder = ClaimsEvidencePackBuilder(
            policy_reference=self.policy_reference,
            coverage_condition_ref=self.profile.coverage_condition_ref,
            active_assurance_profile=self.profile,
        )
        builder.set_source_evidences(source_evidences)
        builder.set_action(action)
        builder.set_evaluation(evaluation)
        builder.set_reht_clearance(clearance_output)
        builder.set_racs_decision(
            decision_contract
            if isinstance(decision_contract, dict)
            else {"decision": decision_val}
        )
        builder.set_effect_receipt(exec_output)
        builder.set_veritas_verification(veritas_record)

        claims_pack = builder.build(now=now)

        return ProcurementPipelineResult(
            success=True,
            assurance_evaluation=evaluation,
            reht_clearance=clearance_output,
            racs_decision=decision_contract
            if isinstance(decision_contract, dict)
            else {"decision": decision_val},
            execution_receipt=exec_output,
            veritas_record=veritas_record,
            claims_pack=claims_pack,
        )
