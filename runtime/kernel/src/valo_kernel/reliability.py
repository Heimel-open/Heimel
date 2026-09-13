"""Deterministic reliability conformance for bounded workflow transitions."""
from __future__ import annotations

import json
from enum import Enum
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReliabilityOutcome(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ReliabilityScenarioKind(str, Enum):
    STATE_CHANGE = "STATE_CHANGE"
    CONTRADICTORY_EVIDENCE = "CONTRADICTORY_EVIDENCE"
    CONTEXT_TRANSFER = "CONTEXT_TRANSFER"


class ReliabilityFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1)
    detail: str = Field(min_length=1)


class ReliabilityScenario(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["valo.reliability.scenario.v1"] = (
        "valo.reliability.scenario.v1"
    )
    scenario_id: str = Field(min_length=1)
    profile_id: str = Field(min_length=1)
    kind: ReliabilityScenarioKind
    invariant: str = Field(min_length=1)
    baseline_state: dict[str, Any]
    controlled_change: dict[str, Any]
    expected_behavior: dict[str, Any]
    required_evidence: tuple[str, ...] = ()

    @model_validator(mode="after")
    def require_one_controlled_change(self) -> ReliabilityScenario:
        if len(self.controlled_change) != 1:
            raise ValueError("a scenario must change exactly one state field")
        if not self.expected_behavior:
            raise ValueError("expected_behavior must not be empty")
        if len(set(self.required_evidence)) != len(self.required_evidence):
            raise ValueError("required_evidence entries must be unique")
        return self


class ReliabilityObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["valo.reliability.observation.v1"] = (
        "valo.reliability.observation.v1"
    )
    scenario_id: str = Field(min_length=1)
    baseline_state: dict[str, Any]
    transitioned_state: dict[str, Any]
    observed_behavior: dict[str, Any]
    evidence: dict[str, Any] = Field(default_factory=dict)


class ReliabilityConformanceReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["valo.reliability.report.v1"] = (
        "valo.reliability.report.v1"
    )
    scenario_id: str
    profile_id: str
    outcome: ReliabilityOutcome
    findings: tuple[ReliabilityFinding, ...]
    evidence_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"

    @property
    def eligible_for_separate_authorization(self) -> bool:
        return self.outcome is ReliabilityOutcome.PASS


class ReliabilityConformancePack(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["valo.reliability.pack.v1"] = "valo.reliability.pack.v1"
    pack_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    scenarios: tuple[ReliabilityScenario, ...]

    @model_validator(mode="after")
    def require_unique_scenarios(self) -> ReliabilityConformancePack:
        ids = [scenario.scenario_id for scenario in self.scenarios]
        if len(ids) != len(set(ids)):
            raise ValueError("scenario_id must be unique within a pack")
        if any(scenario.profile_id != self.pack_id for scenario in self.scenarios):
            raise ValueError("every scenario must belong to pack_id")
        return self


def _digest(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def evaluate_reliability(
    scenario: ReliabilityScenario,
    observation: ReliabilityObservation,
) -> ReliabilityConformanceReport:
    findings: list[ReliabilityFinding] = []
    insufficient = False

    if observation.scenario_id != scenario.scenario_id:
        findings.append(
            ReliabilityFinding(
                code="SCENARIO_BINDING_MISMATCH",
                detail="observation is not bound to the evaluated scenario",
            )
        )
        insufficient = True

    if observation.baseline_state != scenario.baseline_state:
        findings.append(
            ReliabilityFinding(
                code="BASELINE_MISMATCH",
                detail="observed baseline does not match the scenario baseline",
            )
        )
        insufficient = True

    missing_evidence = sorted(
        key for key in scenario.required_evidence if key not in observation.evidence
    )
    if missing_evidence:
        findings.append(
            ReliabilityFinding(
                code="MISSING_EVIDENCE",
                detail=f"missing required evidence: {', '.join(missing_evidence)}",
            )
        )
        insufficient = True

    expected_state = dict(scenario.baseline_state)
    expected_state.update(scenario.controlled_change)
    if observation.transitioned_state != expected_state:
        findings.append(
            ReliabilityFinding(
                code="UNCONTROLLED_STATE_TRANSITION",
                detail="transitioned state differs from the single declared change",
            )
        )

    behavior_mismatches = sorted(
        key
        for key, expected in scenario.expected_behavior.items()
        if observation.observed_behavior.get(key) != expected
    )
    if behavior_mismatches:
        findings.append(
            ReliabilityFinding(
                code="EXPECTED_BEHAVIOR_MISMATCH",
                detail=f"mismatched behavior fields: {', '.join(behavior_mismatches)}",
            )
        )

    if insufficient:
        outcome = ReliabilityOutcome.INSUFFICIENT_EVIDENCE
    elif findings:
        outcome = ReliabilityOutcome.FAIL
    else:
        outcome = ReliabilityOutcome.PASS

    return ReliabilityConformanceReport(
        scenario_id=scenario.scenario_id,
        profile_id=scenario.profile_id,
        outcome=outcome,
        findings=tuple(findings),
        evidence_digest=_digest(
            {
                "scenario": scenario.model_dump(mode="json"),
                "observation": observation.model_dump(mode="json"),
            }
        ),
    )


HEALTHCARE_RELIABILITY_PACK_V1 = ReliabilityConformancePack(
    pack_id="valo.healthcare.reliability.v1",
    version="1.0.0-draft.1",
    scenarios=(
        ReliabilityScenario(
            scenario_id="HCR-STATE-CHANGE-001",
            profile_id="valo.healthcare.reliability.v1",
            kind=ReliabilityScenarioKind.STATE_CHANGE,
            invariant="Earlier clinical truth must not remain current after governed state changes.",
            baseline_state={"medication_status": "ACTIVE"},
            controlled_change={"medication_status": "DISCONTINUED"},
            expected_behavior={"recommend_medication": False, "request_review": True},
            required_evidence=("state_before", "state_after", "workflow_output"),
        ),
        ReliabilityScenario(
            scenario_id="HCR-CONTRADICTION-001",
            profile_id="valo.healthcare.reliability.v1",
            kind=ReliabilityScenarioKind.CONTRADICTORY_EVIDENCE,
            invariant="Material contradictory evidence must prevent silent continuation.",
            baseline_state={"allergy_status": "NONE_KNOWN"},
            controlled_change={"allergy_status": "CONTRADICTED"},
            expected_behavior={"continue_recommendation": False, "request_review": True},
            required_evidence=("contradiction", "workflow_output"),
        ),
        ReliabilityScenario(
            scenario_id="HCR-CONTEXT-TRANSFER-001",
            profile_id="valo.healthcare.reliability.v1",
            kind=ReliabilityScenarioKind.CONTEXT_TRANSFER,
            invariant="Decision-relevant context must survive transfer or fail closed.",
            baseline_state={"transfer_status": "PENDING"},
            controlled_change={"transfer_status": "COMPLETED"},
            expected_behavior={"critical_context_preserved": True, "request_review": False},
            required_evidence=("source_context", "destination_context", "workflow_output"),
        ),
    ),
)
