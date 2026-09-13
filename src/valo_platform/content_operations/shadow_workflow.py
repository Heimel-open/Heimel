"""End-to-end shadow workflow for Governed Content Operations.

The runner composes existing observation, policy, batch, and binding evidence.
It performs no production write, issues no clearance, creates no CommitToken,
and deliberately does not create an ExecutionReceipt for simulation.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Sequence

import rfc8785
from pydantic import BaseModel, ConfigDict, Field

from src.valo_platform.action_envelope.models import ActionDecision
from src.valo_platform.connectors.content.synthetic import (
    ContentShadowEvidence,
    SyntheticContentShadowConnector,
)

from .actions import ContentActionCase
from .batch_evaluation import ContentBatchEvaluation, ContentBatchEvaluator
from .content_policy import (
    ContentPolicyEvaluation,
    ContentPolicyEvaluator,
    ContentPolicyProfile,
    ContentRiskEvidence,
)
from .invalidation import (
    ContentBindingObservation,
    ContentBindingSnapshot,
    ContentBindingValidator,
    ContentInvalidationEvidence,
)


_ZERO_DIGEST = "sha256:" + "0" * 64


class ContentEvidenceStage(str, Enum):
    ACTION_CASE = "action_case"
    OBSERVATION = "observation"
    POLICY_RECOMMENDATION = "policy_recommendation"
    DRY_RUN_SIMULATION = "dry_run_simulation"
    BINDING_SNAPSHOT = "binding_snapshot"
    BINDING_VALIDITY = "binding_validity"
    AGGREGATE_BATCH = "aggregate_batch"


class ContentEvidenceLink(BaseModel):
    """One deterministic link over an existing shadow evidence artifact."""

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)

    workflow_ref: str = Field(min_length=1)
    sequence: int = Field(ge=0)
    stage: ContentEvidenceStage
    artifact_type: str = Field(min_length=1)
    subject_ref: str = Field(min_length=1)
    artifact_digest: str
    previous_chain_digest: str
    chain_digest: str

    def chain_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"chain_digest"})

    def verify(self) -> bool:
        return self.chain_digest == _digest(self.chain_payload())


class ContentShadowWorkflowItem(BaseModel):
    """Reference-only result for one shadow-evaluated content action."""

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)

    action_id: str
    action_payload_digest: str
    observation_evidence_digest: str
    policy_decision: ActionDecision
    policy_reasons: tuple[str, ...]
    policy_evaluation_digest: str
    simulation_evidence_digest: str
    simulation_would_mutate: bool
    binding_snapshot_digest: str
    binding_valid: bool
    invalidation_evidence_digest: str
    execution_authorized: Literal[False] = False
    production_writes: Literal[0] = 0


class ContentShadowWorkflowResult(BaseModel):
    """Complete deterministic shadow result with no execution authority."""

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)

    workflow_ref: str = Field(min_length=1)
    item_results: tuple[ContentShadowWorkflowItem, ...] = Field(min_length=1)
    batch_decision: ActionDecision
    batch_reasons: tuple[str, ...]
    batch_evaluation_digest: str
    evidence_links: tuple[ContentEvidenceLink, ...] = Field(min_length=1)
    final_chain_digest: str
    evaluated_at: datetime
    execution_authorized: Literal[False] = False
    production_writes: Literal[0] = 0

    def verify_chain(self) -> bool:
        previous = _ZERO_DIGEST
        for expected_sequence, link in enumerate(self.evidence_links):
            if link.sequence != expected_sequence:
                return False
            if link.workflow_ref != self.workflow_ref:
                return False
            if link.previous_chain_digest != previous:
                return False
            if not link.verify():
                return False
            previous = link.chain_digest
        return previous == self.final_chain_digest


class ContentShadowWorkflowError(RuntimeError):
    """The shadow workflow received inconsistent evidence or bindings."""


class ContentShadowWorkflowRunner:
    """Compose the full network-free content governance shadow path."""

    def __init__(
        self,
        *,
        connector: SyntheticContentShadowConnector,
        policy_evaluator: ContentPolicyEvaluator | None = None,
        batch_evaluator: ContentBatchEvaluator | None = None,
        binding_validator: ContentBindingValidator | None = None,
    ) -> None:
        self._connector = connector
        self._policy_evaluator = policy_evaluator or ContentPolicyEvaluator()
        self._batch_evaluator = batch_evaluator or ContentBatchEvaluator()
        self._binding_validator = binding_validator or ContentBindingValidator()

    def run(
        self,
        *,
        workflow_ref: str,
        action_cases: Sequence[ContentActionCase],
        policy: ContentPolicyProfile,
        risk_evidence: Sequence[ContentRiskEvidence],
        now: datetime | None = None,
    ) -> ContentShadowWorkflowResult:
        if not workflow_ref.strip():
            raise ValueError("workflow_ref is required")
        if not action_cases:
            raise ValueError("shadow workflow requires at least one Action Case")
        if len(action_cases) != len(risk_evidence):
            raise ValueError("action cases and risk evidence must align")

        evaluated_at = _as_utc(now or datetime.now(timezone.utc))
        observations: list[ContentShadowEvidence] = []
        evaluations: list[ContentPolicyEvaluation] = []
        simulations: list[ContentShadowEvidence] = []
        snapshots: list[ContentBindingSnapshot] = []
        validity_results: list[ContentInvalidationEvidence] = []

        for action_case, risk in zip(action_cases, risk_evidence):
            observation = self._connector.observe_current_state(action_case)
            self._require_evidence_binding(action_case, observation)
            observations.append(observation)

            evaluation = self._policy_evaluator.evaluate(
                action_case=action_case,
                policy=policy,
                risk=risk,
                now=evaluated_at,
            )
            evaluations.append(evaluation)

            simulation = self._connector.dry_run(action_case)
            self._require_evidence_binding(action_case, simulation)
            if not simulation.dry_run:
                raise ContentShadowWorkflowError(
                    "shadow simulation evidence is not marked as dry-run"
                )
            simulations.append(simulation)

            snapshot = ContentBindingSnapshot.capture(
                action_case=action_case,
                policy=policy,
                captured_at=evaluated_at,
            )
            current = ContentBindingObservation.observe(
                action_case=action_case,
                policy=policy,
                observed_at=evaluated_at,
            )
            validity = self._binding_validator.evaluate(
                snapshot=snapshot,
                observation=current,
                now=evaluated_at,
            )
            if not validity.valid:
                raise ContentShadowWorkflowError(
                    "authoritative bindings changed during shadow evaluation"
                )
            snapshots.append(snapshot)
            validity_results.append(validity)

        batch = self._batch_evaluator.evaluate(
            action_cases=action_cases,
            item_evaluations=evaluations,
            risk_evidence=risk_evidence,
            policy=policy,
            now=evaluated_at,
        )

        links = self._build_links(
            workflow_ref=workflow_ref,
            action_cases=action_cases,
            observations=observations,
            evaluations=evaluations,
            simulations=simulations,
            snapshots=snapshots,
            validity_results=validity_results,
            batch=batch,
        )
        items = tuple(
            ContentShadowWorkflowItem(
                action_id=action_case.action_case.case_id,
                action_payload_digest=action_case.digest(),
                observation_evidence_digest=observation.digest(),
                policy_decision=evaluation.decision,
                policy_reasons=evaluation.reasons,
                policy_evaluation_digest=_model_digest(
                    evaluation, exclude={"evaluated_at"}
                ),
                simulation_evidence_digest=simulation.digest(),
                simulation_would_mutate=simulation.would_mutate,
                binding_snapshot_digest=snapshot.digest(),
                binding_valid=validity.valid,
                invalidation_evidence_digest=_model_digest(
                    validity, exclude={"checked_at"}
                ),
            )
            for action_case, observation, evaluation, simulation, snapshot, validity in zip(
                action_cases,
                observations,
                evaluations,
                simulations,
                snapshots,
                validity_results,
            )
        )
        result = ContentShadowWorkflowResult(
            workflow_ref=workflow_ref,
            item_results=items,
            batch_decision=batch.decision,
            batch_reasons=batch.reasons,
            batch_evaluation_digest=_model_digest(
                batch, exclude={"evaluated_at"}
            ),
            evidence_links=links,
            final_chain_digest=links[-1].chain_digest,
            evaluated_at=evaluated_at,
        )
        if not result.verify_chain():
            raise ContentShadowWorkflowError("constructed evidence chain is invalid")
        return result

    @staticmethod
    def _require_evidence_binding(
        action_case: ContentActionCase,
        evidence: ContentShadowEvidence,
    ) -> None:
        expected = (
            action_case.action_case.case_id,
            action_case.digest(),
            action_case.target_digest(),
            action_case.state_binding_digest(),
        )
        actual = (
            evidence.action_id,
            evidence.payload_digest,
            evidence.target_digest,
            evidence.state_binding_digest,
        )
        if actual != expected:
            raise ContentShadowWorkflowError(
                "shadow evidence does not bind the exact Content Action Case"
            )

    @staticmethod
    def _build_links(
        *,
        workflow_ref: str,
        action_cases: Sequence[ContentActionCase],
        observations: Sequence[ContentShadowEvidence],
        evaluations: Sequence[ContentPolicyEvaluation],
        simulations: Sequence[ContentShadowEvidence],
        snapshots: Sequence[ContentBindingSnapshot],
        validity_results: Sequence[ContentInvalidationEvidence],
        batch: ContentBatchEvaluation,
    ) -> tuple[ContentEvidenceLink, ...]:
        artifacts: list[tuple[ContentEvidenceStage, str, str, str]] = []
        for action_case, observation, evaluation, simulation, snapshot, validity in zip(
            action_cases,
            observations,
            evaluations,
            simulations,
            snapshots,
            validity_results,
        ):
            action_ref = action_case.action_case.case_id
            artifacts.extend(
                (
                    (
                        ContentEvidenceStage.ACTION_CASE,
                        "ContentActionCase",
                        action_ref,
                        action_case.digest(),
                    ),
                    (
                        ContentEvidenceStage.OBSERVATION,
                        "ContentShadowEvidence",
                        action_ref,
                        observation.digest(),
                    ),
                    (
                        ContentEvidenceStage.POLICY_RECOMMENDATION,
                        "ContentPolicyEvaluation",
                        action_ref,
                        _model_digest(evaluation, exclude={"evaluated_at"}),
                    ),
                    (
                        ContentEvidenceStage.DRY_RUN_SIMULATION,
                        "ContentShadowEvidence",
                        action_ref,
                        simulation.digest(),
                    ),
                    (
                        ContentEvidenceStage.BINDING_SNAPSHOT,
                        "ContentBindingSnapshot",
                        action_ref,
                        snapshot.digest(),
                    ),
                    (
                        ContentEvidenceStage.BINDING_VALIDITY,
                        "ContentInvalidationEvidence",
                        action_ref,
                        _model_digest(validity, exclude={"checked_at"}),
                    ),
                )
            )
        artifacts.append(
            (
                ContentEvidenceStage.AGGREGATE_BATCH,
                "ContentBatchEvaluation",
                f"batch:{workflow_ref}",
                _model_digest(batch, exclude={"evaluated_at"}),
            )
        )

        links: list[ContentEvidenceLink] = []
        previous = _ZERO_DIGEST
        for sequence, (stage, artifact_type, subject_ref, artifact_digest) in enumerate(
            artifacts
        ):
            provisional = {
                "workflow_ref": workflow_ref,
                "sequence": sequence,
                "stage": stage.value,
                "artifact_type": artifact_type,
                "subject_ref": subject_ref,
                "artifact_digest": artifact_digest,
                "previous_chain_digest": previous,
            }
            link = ContentEvidenceLink(
                **provisional,
                chain_digest=_digest(provisional),
            )
            links.append(link)
            previous = link.chain_digest
        return tuple(links)


def _model_digest(model: BaseModel, *, exclude: set[str] | None = None) -> str:
    payload = model.model_dump(mode="json", exclude=exclude or set())
    return _digest(payload)


def _digest(payload: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(rfc8785.dumps(payload)).hexdigest()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("time must be timezone-aware")
    return value.astimezone(timezone.utc)
