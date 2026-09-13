"""Post-training lifecycle contracts for governed model creation.

The existing Unsloth adapter owns validation of the pre-execution handoff.
This module starts at the resulting governed PEP handoff and preserves lineage
through candidate creation, Honest Evaluation, MAL admission and runtime
registry eligibility. Training success never admits a model by itself.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Mapping, Sequence


FACTORY_CONTRACT = "valo.governed-model-factory.v1"
CANDIDATE_CONTRACT = "valo.model-candidate-receipt.v1"
ADMISSION_CONTRACT = "valo.model-admission-record.v1"
GOVERNANCE_ORDER = ("VAIG", "reht", "RACS", "PEP")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ModelLifecycleError(ValueError):
    """Raised when model lifecycle evidence is incomplete or unbound."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ModelLifecycleError(f"{field} must be an object")
    return value


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ModelLifecycleError(f"{field} must be a non-empty string")
    return value.strip()


def _digest(value: Any, field: str) -> str:
    text = _text(value, field).lower()
    if not HEX64.fullmatch(text):
        raise ModelLifecycleError(f"{field} must be a lowercase sha256 digest")
    return text


def _text_list(value: Any, field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ModelLifecycleError(f"{field} must be a list")
    result = tuple(_text(item, f"{field}[]") for item in value)
    if not allow_empty and not result:
        raise ModelLifecycleError(f"{field} must not be empty")
    return result


@dataclass(frozen=True)
class CandidateModelReceipt:
    candidate_id: str
    artifact_digest: str
    pep_handoff_digest: str
    execution_receipt_digest: str
    workspace_digest: str
    state_digest: str
    dataset_digest: str
    provenance: tuple[str, ...]
    engine_id: str
    engine_commit: str
    runtime_digest: str
    objective: str
    output_name: str
    state: str = "CANDIDATE"
    contract: str = CANDIDATE_CONTRACT

    @classmethod
    def issue(
        cls,
        handoff: Mapping[str, Any],
        *,
        candidate_id: str,
        artifact_digest: str,
        execution_receipt_digest: str,
    ) -> "CandidateModelReceipt":
        handoff = _mapping(handoff, "handoff")
        if handoff.get("contract") != FACTORY_CONTRACT:
            raise ModelLifecycleError("unsupported model-factory handoff contract")

        pep = _mapping(handoff.get("pep_handoff"), "handoff.pep_handoff")
        if pep.get("may_execute") is not True:
            raise ModelLifecycleError(
                "NULL_EFFECT_ON_DENY: candidate cannot be created without an executable PEP handoff"
            )
        if pep.get("max_attempts") != 1:
            raise ModelLifecycleError("candidate lineage requires max_attempts=1")
        handoff_digest = _digest(
            pep.get("handoff_digest"), "handoff.pep_handoff.handoff_digest"
        )
        handoff_core = dict(handoff)
        handoff_core.pop("pep_handoff", None)
        if digest(handoff_core) != handoff_digest:
            raise ModelLifecycleError(
                "PEP handoff digest does not bind the exact model-factory action"
            )

        promotion = _mapping(handoff.get("promotion"), "handoff.promotion")
        if (
            promotion.get("mode") != "candidate_only"
            or promotion.get("automatic") is not False
            or promotion.get("requires_new_admission") is not True
        ):
            raise ModelLifecycleError(
                "CANDIDATE_NOT_ADMITTED: factory handoff must require new admission"
            )

        governance_raw = handoff.get("governance")
        if not isinstance(governance_raw, list) or len(governance_raw) != 4:
            raise ModelLifecycleError("handoff.governance must contain four receipts")
        stages: list[str] = []
        for index, entry in enumerate(governance_raw):
            entry = _mapping(entry, f"handoff.governance[{index}]")
            stages.append(_text(entry.get("stage"), f"handoff.governance[{index}].stage"))
            if _text(
                entry.get("decision"), f"handoff.governance[{index}].decision"
            ).upper() != "ALLOW":
                raise ModelLifecycleError(
                    "NULL_EFFECT_ON_DENY: all governed stages must ALLOW candidate creation"
                )
            _digest(
                entry.get("receipt_digest"),
                f"handoff.governance[{index}].receipt_digest",
            )
        if tuple(stages) != GOVERNANCE_ORDER:
            raise ModelLifecycleError(
                "governance chain must be VAIG -> reht -> RACS -> PEP"
            )

        workspace = _mapping(handoff.get("workspace"), "handoff.workspace")
        state = _mapping(handoff.get("state_admission"), "handoff.state_admission")
        if _text(state.get("status"), "handoff.state_admission.status").upper() != "ADMITTED":
            raise ModelLifecycleError("source state must remain ADMITTED")
        provenance_raw = state.get("provenance")
        if not isinstance(provenance_raw, list) or not provenance_raw:
            raise ModelLifecycleError("source provenance must not be empty")
        provenance = tuple(
            _digest(item, f"handoff.state_admission.provenance[{index}]")
            for index, item in enumerate(provenance_raw)
        )

        training = _mapping(handoff.get("training_spec"), "handoff.training_spec")
        engine = _mapping(handoff.get("engine"), "handoff.engine")

        return cls(
            candidate_id=_text(candidate_id, "candidate_id"),
            artifact_digest=_digest(artifact_digest, "artifact_digest"),
            pep_handoff_digest=handoff_digest,
            execution_receipt_digest=_digest(
                execution_receipt_digest, "execution_receipt_digest"
            ),
            workspace_digest=_digest(
                workspace.get("workspace_digest"), "handoff.workspace.workspace_digest"
            ),
            state_digest=_digest(
                state.get("state_digest"), "handoff.state_admission.state_digest"
            ),
            dataset_digest=_digest(
                training.get("dataset_digest"), "handoff.training_spec.dataset_digest"
            ),
            provenance=provenance,
            engine_id=_text(engine.get("engine_id"), "handoff.engine.engine_id"),
            engine_commit=_text(engine.get("commit"), "handoff.engine.commit"),
            runtime_digest=_digest(
                engine.get("runtime_digest"), "handoff.engine.runtime_digest"
            ),
            objective=_text(training.get("objective"), "handoff.training_spec.objective"),
            output_name=_text(
                training.get("output_name"), "handoff.training_spec.output_name"
            ),
        )

    @property
    def receipt_digest(self) -> str:
        return digest(asdict(self))


@dataclass(frozen=True)
class HonestEvaluationEvidence:
    evaluation_ref: str
    candidate_id: str
    candidate_receipt_digest: str
    evidence_digest: str
    evaluator_id: str
    passed: bool

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "HonestEvaluationEvidence":
        value = _mapping(value, "evaluation")
        passed = value.get("passed")
        if not isinstance(passed, bool):
            raise ModelLifecycleError("evaluation.passed must be boolean")
        return cls(
            evaluation_ref=_text(value.get("evaluation_ref"), "evaluation.evaluation_ref"),
            candidate_id=_text(value.get("candidate_id"), "evaluation.candidate_id"),
            candidate_receipt_digest=_digest(
                value.get("candidate_receipt_digest"),
                "evaluation.candidate_receipt_digest",
            ),
            evidence_digest=_digest(
                value.get("evidence_digest"), "evaluation.evidence_digest"
            ),
            evaluator_id=_text(value.get("evaluator_id"), "evaluation.evaluator_id"),
            passed=passed,
        )


@dataclass(frozen=True)
class MALDecision:
    decision_ref: str
    candidate_id: str
    candidate_receipt_digest: str
    decision: str
    domain: str
    exclusions: tuple[str, ...]
    owner: str
    risk_owner: str
    review_date: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "MALDecision":
        value = _mapping(value, "mal")
        decision = _text(value.get("decision"), "mal.decision").upper()
        if decision not in {"ADMIT", "REJECT", "DEFER"}:
            raise ModelLifecycleError("mal.decision must be ADMIT, REJECT or DEFER")
        return cls(
            decision_ref=_text(value.get("decision_ref"), "mal.decision_ref"),
            candidate_id=_text(value.get("candidate_id"), "mal.candidate_id"),
            candidate_receipt_digest=_digest(
                value.get("candidate_receipt_digest"),
                "mal.candidate_receipt_digest",
            ),
            decision=decision,
            domain=_text(value.get("domain"), "mal.domain"),
            exclusions=_text_list(
                value.get("exclusions", []), "mal.exclusions", allow_empty=True
            ),
            owner=_text(value.get("owner"), "mal.owner"),
            risk_owner=_text(value.get("risk_owner"), "mal.risk_owner"),
            review_date=_text(value.get("review_date"), "mal.review_date"),
        )


@dataclass(frozen=True)
class AdmittedModelRecord:
    model_id: str
    artifact_digest: str
    candidate_id: str
    candidate_receipt_digest: str
    pep_handoff_digest: str
    execution_receipt_digest: str
    workspace_digest: str
    state_digest: str
    dataset_digest: str
    provenance: tuple[str, ...]
    engine_id: str
    engine_commit: str
    runtime_digest: str
    evaluation_ref: str
    evaluation_evidence_digest: str
    mal_decision_ref: str
    domain: str
    exclusions: tuple[str, ...]
    owner: str
    risk_owner: str
    review_date: str
    state: str = "ADMITTED"
    contract: str = ADMISSION_CONTRACT

    @property
    def registry_digest(self) -> str:
        return digest(asdict(self))


def promote_candidate(
    candidate: CandidateModelReceipt,
    *,
    model_id: str,
    evaluation: HonestEvaluationEvidence,
    mal: MALDecision,
) -> AdmittedModelRecord:
    """Create a registry-eligible model record only after evaluation and MAL."""

    if candidate.state != "CANDIDATE":
        raise ModelLifecycleError("promotion input must be a candidate model")

    candidate_digest = candidate.receipt_digest
    for source_name, source_id, source_digest in (
        (
            "evaluation",
            evaluation.candidate_id,
            evaluation.candidate_receipt_digest,
        ),
        ("mal", mal.candidate_id, mal.candidate_receipt_digest),
    ):
        if source_id != candidate.candidate_id or source_digest != candidate_digest:
            raise ModelLifecycleError(
                f"{source_name} evidence is not bound to this candidate"
            )

    if not evaluation.passed:
        raise ModelLifecycleError(
            "CANDIDATE_NOT_ADMITTED: Honest Evaluation did not pass"
        )
    if mal.decision != "ADMIT":
        raise ModelLifecycleError(
            f"CANDIDATE_NOT_ADMITTED: MAL decision is {mal.decision}"
        )

    return AdmittedModelRecord(
        model_id=_text(model_id, "model_id"),
        artifact_digest=candidate.artifact_digest,
        candidate_id=candidate.candidate_id,
        candidate_receipt_digest=candidate_digest,
        pep_handoff_digest=candidate.pep_handoff_digest,
        execution_receipt_digest=candidate.execution_receipt_digest,
        workspace_digest=candidate.workspace_digest,
        state_digest=candidate.state_digest,
        dataset_digest=candidate.dataset_digest,
        provenance=candidate.provenance,
        engine_id=candidate.engine_id,
        engine_commit=candidate.engine_commit,
        runtime_digest=candidate.runtime_digest,
        evaluation_ref=evaluation.evaluation_ref,
        evaluation_evidence_digest=evaluation.evidence_digest,
        mal_decision_ref=mal.decision_ref,
        domain=mal.domain,
        exclusions=mal.exclusions,
        owner=mal.owner,
        risk_owner=mal.risk_owner,
        review_date=mal.review_date,
    )


def require_runtime_admitted(value: Any) -> AdmittedModelRecord:
    """Fail closed when a candidate is presented to runtime placement."""

    if not isinstance(value, AdmittedModelRecord) or value.state != "ADMITTED":
        raise ModelLifecycleError(
            "CANDIDATE_NOT_ADMITTED: runtime placement requires an ADMITTED model"
        )
    return value
