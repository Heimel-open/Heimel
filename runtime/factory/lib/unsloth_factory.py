"""Governed model-factory adapter with Unsloth as a replaceable engine.

This module does not execute training and grants no authority. It validates an
already-governed work unit and produces a deterministic PEP handoff. The actual
training engine remains replaceable and is identified by an attested runtime
reference.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


CONTRACT = "valo.governed-model-factory.v1"
UNSLOTH_REPO = "nsolland/unsloth"
UNSLOTH_COMMIT = "993e3e4529fc5796ef945d8c2b5af7b75ccfbf4f"
GOVERNANCE_ORDER = ("VAIG", "reht", "RACS", "PEP")
RACS_OUTCOMES = {"ALLOW", "MODIFY", "DEFER", "DENY", "STEP_UP", "HALT"}
CANDIDATE_PROMOTION_GATES = ("EVALUATION", "NEGATIVE_TESTING", "MAL_ADMISSION")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")


class GovernanceError(ValueError):
    """Raised when the work unit is not admissible for a PEP handoff."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GovernanceError(f"{field} must be a non-empty string")
    return value.strip()


def _require_digest(value: Any, field: str) -> str:
    text = _require_text(value, field).lower()
    if not HEX64.fullmatch(text):
        raise GovernanceError(f"{field} must be a lowercase sha256 digest")
    return text


def _require_probability(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GovernanceError(f"{field} must be a number between 0 and 1")
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise GovernanceError(f"{field} must be a finite number between 0 and 1")
    return number


def _require_nonnegative_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GovernanceError(f"{field} must be a non-negative number")
    number = float(value)
    if not math.isfinite(number) or number < 0.0:
        raise GovernanceError(f"{field} must be a finite non-negative number")
    return number


@dataclass(frozen=True)
class EngineRef:
    engine_id: str
    repo: str
    commit: str
    runtime_digest: str
    attestor: str
    attestation_receipt_digest: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "EngineRef":
        engine_id = _require_text(value.get("engine_id"), "engine.engine_id")
        repo = _require_text(value.get("repo"), "engine.repo")
        commit = _require_text(value.get("commit"), "engine.commit").lower()
        if not HEX40.fullmatch(commit):
            raise GovernanceError("engine.commit must be a 40-character lowercase git SHA")
        runtime_digest = _require_digest(value.get("runtime_digest"), "engine.runtime_digest")
        attestor = _require_text(value.get("attestor"), "engine.attestor")
        receipt = _require_digest(
            value.get("attestation_receipt_digest"),
            "engine.attestation_receipt_digest",
        )
        return cls(engine_id, repo, commit, runtime_digest, attestor, receipt)

    @classmethod
    def pinned_unsloth(
        cls,
        *,
        runtime_digest: str,
        attestor: str,
        attestation_receipt_digest: str,
    ) -> "EngineRef":
        return cls.from_mapping(
            {
                "engine_id": "unsloth",
                "repo": UNSLOTH_REPO,
                "commit": UNSLOTH_COMMIT,
                "runtime_digest": runtime_digest,
                "attestor": attestor,
                "attestation_receipt_digest": attestation_receipt_digest,
            }
        )

    def identity(self) -> dict[str, str]:
        return {
            "engine_id": self.engine_id,
            "repo": self.repo,
            "commit": self.commit,
            "runtime_digest": self.runtime_digest,
            "attestor": self.attestor,
            "attestation_receipt_digest": self.attestation_receipt_digest,
        }


@dataclass(frozen=True)
class StateAdmission:
    status: str
    state_digest: str
    admission_receipt_digest: str
    provenance: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "StateAdmission":
        status = _require_text(value.get("status"), "state_admission.status").upper()
        if status != "ADMITTED":
            raise GovernanceError("state must be ADMITTED before model-factory use")
        state_digest = _require_digest(value.get("state_digest"), "state_admission.state_digest")
        receipt = _require_digest(
            value.get("admission_receipt_digest"),
            "state_admission.admission_receipt_digest",
        )
        provenance_raw = value.get("provenance")
        if not isinstance(provenance_raw, list) or not provenance_raw:
            raise GovernanceError("state_admission.provenance must be a non-empty list")
        provenance = tuple(
            _require_digest(item, f"state_admission.provenance[{index}]")
            for index, item in enumerate(provenance_raw)
        )
        return cls(status, state_digest, receipt, provenance)


@dataclass(frozen=True)
class GovernedWorkspace:
    workspace_id: str
    workspace_digest: str
    purpose_id: str
    authority_ref: str
    authority_receipt_digest: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "GovernedWorkspace":
        return cls(
            workspace_id=_require_text(value.get("workspace_id"), "workspace.workspace_id"),
            workspace_digest=_require_digest(value.get("workspace_digest"), "workspace.workspace_digest"),
            purpose_id=_require_text(value.get("purpose_id"), "workspace.purpose_id"),
            authority_ref=_require_text(value.get("authority_ref"), "workspace.authority_ref"),
            authority_receipt_digest=_require_digest(
                value.get("authority_receipt_digest"),
                "workspace.authority_receipt_digest",
            ),
        )


@dataclass(frozen=True)
class GateReceipt:
    stage: str
    decision: str
    receipt_digest: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "GateReceipt":
        stage = _require_text(value.get("stage"), "governance.stage")
        decision = _require_text(value.get("decision"), f"governance.{stage}.decision").upper()
        if decision not in RACS_OUTCOMES:
            raise GovernanceError(f"unsupported governance decision: {decision}")
        receipt = _require_digest(value.get("receipt_digest"), f"governance.{stage}.receipt_digest")
        return cls(stage, decision, receipt)


def validate_governance_chain(receipts: Sequence[GateReceipt]) -> tuple[GateReceipt, ...]:
    chain = tuple(receipts)
    if tuple(item.stage for item in chain) != GOVERNANCE_ORDER:
        raise GovernanceError("governance chain must be VAIG -> reht -> RACS -> PEP")
    for item in chain[:3]:
        if item.decision != "ALLOW":
            raise GovernanceError(f"{item.stage} decision is {item.decision}; execution is not admissible")
    if chain[3].decision != "ALLOW":
        raise GovernanceError("PEP must explicitly enforce ALLOW for this handoff")
    return chain


def _validate_reopd_recipe(value: Any) -> dict[str, Any]:
    """Validate provider-neutral offline ReOPD controls inside the existing factory."""

    if not isinstance(value, Mapping):
        raise GovernanceError("training_spec.recipe must be an object")
    allowed = {
        "name",
        "base_model_digest",
        "teacher",
        "trajectories",
        "prefix_sampling",
        "distribution_shift_measurements",
        "environment_mode",
        "live_environment_calls",
        "consequence_bearing_tool_calls",
    }
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise GovernanceError(
            "training_spec.recipe contains unknown fields: " + ", ".join(unknown)
        )
    name = _require_text(value.get("name"), "training_spec.recipe.name").lower()
    if name != "reopd":
        raise GovernanceError("only the provider-neutral reopd recipe is supported")
    base_model_digest = _require_digest(
        value.get("base_model_digest"),
        "training_spec.recipe.base_model_digest",
    )

    teacher_raw = value.get("teacher")
    if not isinstance(teacher_raw, Mapping):
        raise GovernanceError("training_spec.recipe.teacher must be an object")
    teacher_allowed = {
        "version",
        "reliability",
        "minimum_reliability",
        "reliability_receipt_digest",
    }
    teacher_unknown = sorted(set(teacher_raw) - teacher_allowed)
    if teacher_unknown:
        raise GovernanceError(
            "training_spec.recipe.teacher contains unknown fields: "
            + ", ".join(teacher_unknown)
        )
    teacher_version = _require_text(
        teacher_raw.get("version"), "training_spec.recipe.teacher.version"
    )
    reliability = _require_probability(
        teacher_raw.get("reliability"),
        "training_spec.recipe.teacher.reliability",
    )
    minimum_reliability = _require_probability(
        teacher_raw.get("minimum_reliability"),
        "training_spec.recipe.teacher.minimum_reliability",
    )
    reliability_receipt_digest = _require_digest(
        teacher_raw.get("reliability_receipt_digest"),
        "training_spec.recipe.teacher.reliability_receipt_digest",
    )
    if reliability < minimum_reliability:
        raise GovernanceError("teacher reliability is below the policy threshold")

    trajectories_raw = value.get("trajectories")
    if not isinstance(trajectories_raw, list) or not trajectories_raw:
        raise GovernanceError("training_spec.recipe.trajectories must be a non-empty list")
    accepted: list[dict[str, Any]] = []
    excluded: list[str] = []
    seen_trajectories: set[str] = set()
    trajectory_allowed = {
        "trajectory_digest",
        "provenance_receipt_digest",
        "admission_receipt_digest",
        "admission_status",
        "authorized_for_training",
    }
    for index, raw in enumerate(trajectories_raw):
        field = f"training_spec.recipe.trajectories[{index}]"
        if not isinstance(raw, Mapping):
            raise GovernanceError(f"{field} must be an object")
        trajectory_unknown = sorted(set(raw) - trajectory_allowed)
        if trajectory_unknown:
            raise GovernanceError(
                f"{field} contains unknown fields: " + ", ".join(trajectory_unknown)
            )
        trajectory_digest = _require_digest(
            raw.get("trajectory_digest"), f"{field}.trajectory_digest"
        )
        provenance_receipt_digest = _require_digest(
            raw.get("provenance_receipt_digest"),
            f"{field}.provenance_receipt_digest",
        )
        admission_receipt_digest = _require_digest(
            raw.get("admission_receipt_digest"),
            f"{field}.admission_receipt_digest",
        )
        admission_status = _require_text(
            raw.get("admission_status"), f"{field}.admission_status"
        ).upper()
        if admission_status not in {"ADMITTED", "CANDIDATE", "REJECTED"}:
            raise GovernanceError(f"{field}.admission_status is unsupported")
        authorized = raw.get("authorized_for_training")
        if not isinstance(authorized, bool):
            raise GovernanceError(f"{field}.authorized_for_training must be boolean")
        if trajectory_digest in seen_trajectories:
            raise GovernanceError("trajectory digests must be unique and immutable")
        seen_trajectories.add(trajectory_digest)
        if admission_status != "ADMITTED" or not authorized:
            excluded.append(trajectory_digest)
            continue
        accepted.append(
            {
                "trajectory_digest": trajectory_digest,
                "provenance_receipt_digest": provenance_receipt_digest,
                "admission_receipt_digest": admission_receipt_digest,
            }
        )
    if not accepted:
        raise GovernanceError("no admitted and authorized teacher trajectories remain")

    prefix_raw = value.get("prefix_sampling")
    if not isinstance(prefix_raw, Mapping):
        raise GovernanceError("training_spec.recipe.prefix_sampling must be an object")
    if set(prefix_raw) != {
        "schedule",
        "initial_probability",
        "decay_factor",
        "decay_steps",
        "minimum_probability",
    }:
        raise GovernanceError(
            "prefix_sampling must define schedule, probabilities, decay_factor and decay_steps"
        )
    schedule = _require_text(
        prefix_raw.get("schedule"), "training_spec.recipe.prefix_sampling.schedule"
    ).lower()
    if schedule != "step_decay":
        raise GovernanceError("ReOPD prefix sampling must use step_decay")
    initial_probability = _require_probability(
        prefix_raw.get("initial_probability"),
        "training_spec.recipe.prefix_sampling.initial_probability",
    )
    decay_factor = _require_probability(
        prefix_raw.get("decay_factor"),
        "training_spec.recipe.prefix_sampling.decay_factor",
    )
    if decay_factor == 0.0:
        raise GovernanceError("prefix_sampling.decay_factor must be greater than zero")
    decay_steps = prefix_raw.get("decay_steps")
    if isinstance(decay_steps, bool) or not isinstance(decay_steps, int) or decay_steps <= 0:
        raise GovernanceError("prefix_sampling.decay_steps must be a positive integer")
    minimum_probability = _require_probability(
        prefix_raw.get("minimum_probability"),
        "training_spec.recipe.prefix_sampling.minimum_probability",
    )
    if minimum_probability > initial_probability:
        raise GovernanceError(
            "prefix_sampling.minimum_probability cannot exceed initial_probability"
        )

    measurements_raw = value.get("distribution_shift_measurements")
    if not isinstance(measurements_raw, list) or not measurements_raw:
        raise GovernanceError(
            "training_spec.recipe.distribution_shift_measurements must be non-empty"
        )
    measurements: list[dict[str, Any]] = []
    for index, raw in enumerate(measurements_raw):
        field = f"training_spec.recipe.distribution_shift_measurements[{index}]"
        if not isinstance(raw, Mapping) or set(raw) != {
            "metric",
            "value",
            "measurement_receipt_digest",
        }:
            raise GovernanceError(
                f"{field} must define metric, value and measurement_receipt_digest"
            )
        measurements.append(
            {
                "metric": _require_text(raw.get("metric"), f"{field}.metric"),
                "value": _require_nonnegative_number(raw.get("value"), f"{field}.value"),
                "measurement_receipt_digest": _require_digest(
                    raw.get("measurement_receipt_digest"),
                    f"{field}.measurement_receipt_digest",
                ),
            }
        )

    if value.get("environment_mode") != "offline_replay":
        raise GovernanceError("ReOPD training must use environment_mode=offline_replay")
    if value.get("live_environment_calls") is not False:
        raise GovernanceError("live environment calls are forbidden during ReOPD training")
    if value.get("consequence_bearing_tool_calls") is not False:
        raise GovernanceError(
            "consequence-bearing tool calls are forbidden during ReOPD training"
        )

    return {
        "name": "reopd",
        "base_model_digest": base_model_digest,
        "teacher": {
            "version": teacher_version,
            "reliability": reliability,
            "minimum_reliability": minimum_reliability,
            "reliability_receipt_digest": reliability_receipt_digest,
        },
        "accepted_trajectories": accepted,
        "excluded_trajectory_digests": sorted(excluded),
        "prefix_sampling": {
            "schedule": "step_decay",
            "initial_probability": initial_probability,
            "decay_factor": decay_factor,
            "decay_steps": decay_steps,
            "minimum_probability": minimum_probability,
        },
        "distribution_shift_measurements": measurements,
        "environment_mode": "offline_replay",
        "live_environment_calls": False,
        "consequence_bearing_tool_calls": False,
        "output_standing": "candidate_only",
        "inherits_teacher_authority": False,
        "inherits_teacher_capability": False,
    }


def _validate_training_spec(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise GovernanceError("training_spec must be an object")
    prohibited = {
        "token",
        "auth_token",
        "authorization_token",
        "authority_token",
        "push_to_hub",
        "auto_promote",
        "auto_publish",
        "retry",
        "retries",
        "retry_count",
        "max_retries",
    }
    overlap = prohibited.intersection(value.keys())
    if overlap:
        raise GovernanceError(
            "training_spec contains forbidden control fields: " + ", ".join(sorted(overlap))
        )
    base_model = _require_text(value.get("base_model"), "training_spec.base_model")
    dataset_digest = _require_digest(value.get("dataset_digest"), "training_spec.dataset_digest")
    objective = _require_text(value.get("objective"), "training_spec.objective")
    output_name = _require_text(value.get("output_name"), "training_spec.output_name")
    parameters = value.get("parameters", {})
    if not isinstance(parameters, Mapping):
        raise GovernanceError("training_spec.parameters must be an object")
    forbidden_parameter_keys = prohibited.intersection(parameters.keys())
    if forbidden_parameter_keys:
        raise GovernanceError(
            "training_spec.parameters contains forbidden control fields: "
            + ", ".join(sorted(forbidden_parameter_keys))
        )
    normalized = {
        "base_model": base_model,
        "dataset_digest": dataset_digest,
        "objective": objective,
        "output_name": output_name,
        "parameters": dict(parameters),
    }
    if "recipe" in value:
        normalized["recipe"] = _validate_reopd_recipe(value.get("recipe"))
    return normalized


def _validate_external_adapter(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise GovernanceError("external_adapter must be an object")
    name = _require_text(value.get("name"), "external_adapter.name")
    adapter_digest = _require_digest(value.get("digest"), "external_adapter.digest")
    if value.get("grants_authority") not in (None, False):
        raise GovernanceError("external adapters cannot grant authority")
    return {
        "name": name,
        "digest": adapter_digest,
        "role": "optional_external_adapter",
        "grants_authority": False,
    }


def build_pep_handoff(request: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a governed work unit and return a deterministic PEP handoff.

    The returned document authorizes at most one attempt and never promotes the
    resulting model. Execution remains the responsibility of the configured PEP.
    """

    if not isinstance(request, Mapping):
        raise GovernanceError("request must be an object")

    workspace_raw = request.get("workspace")
    admission_raw = request.get("state_admission")
    engine_raw = request.get("engine")
    governance_raw = request.get("governance")
    if not isinstance(workspace_raw, Mapping):
        raise GovernanceError("workspace must be an object")
    if not isinstance(admission_raw, Mapping):
        raise GovernanceError("state_admission must be an object")
    if not isinstance(engine_raw, Mapping):
        raise GovernanceError("engine must be an object")
    if not isinstance(governance_raw, list):
        raise GovernanceError("governance must be a list")

    workspace = GovernedWorkspace.from_mapping(workspace_raw)
    admission = StateAdmission.from_mapping(admission_raw)
    engine = EngineRef.from_mapping(engine_raw)
    governance = validate_governance_chain(
        [GateReceipt.from_mapping(item) for item in governance_raw if isinstance(item, Mapping)]
    )
    if len(governance) != len(governance_raw):
        raise GovernanceError("each governance entry must be an object")

    if request.get("attempt", 1) != 1:
        raise GovernanceError("only attempt=1 is permitted; hidden retries are forbidden")
    if request.get("auto_promote") not in (None, False):
        raise GovernanceError("automatic promotion is forbidden")

    training_spec = _validate_training_spec(request.get("training_spec", {}))
    external_adapter = _validate_external_adapter(request.get("external_adapter"))

    authority_sources = request.get("authority_sources", ["workspace_authority"])
    if not isinstance(authority_sources, list) or not authority_sources:
        raise GovernanceError("authority_sources must be a non-empty list")
    normalized_sources = [_require_text(item, "authority_sources[]") for item in authority_sources]
    if any("token" in item.lower() for item in normalized_sources):
        raise GovernanceError("tokens cannot be an authority source")

    core = {
        "contract": CONTRACT,
        "workspace": {
            "workspace_id": workspace.workspace_id,
            "workspace_digest": workspace.workspace_digest,
            "purpose_id": workspace.purpose_id,
            "authority_ref": workspace.authority_ref,
            "authority_receipt_digest": workspace.authority_receipt_digest,
        },
        "state_admission": {
            "status": admission.status,
            "state_digest": admission.state_digest,
            "admission_receipt_digest": admission.admission_receipt_digest,
            "provenance": list(admission.provenance),
        },
        "engine": engine.identity(),
        "governance": [
            {
                "stage": item.stage,
                "decision": item.decision,
                "receipt_digest": item.receipt_digest,
            }
            for item in governance
        ],
        "training_spec": training_spec,
        "authority_sources": normalized_sources,
        "attempt": 1,
        "retry_policy": "none",
        "promotion": {
            "mode": "candidate_only",
            "automatic": False,
            "requires_new_admission": True,
            "required_gates": list(CANDIDATE_PROMOTION_GATES),
        },
        "external_adapter": external_adapter,
    }
    handoff_digest = digest(core)
    return {
        **core,
        "pep_handoff": {
            "may_execute": True,
            "max_attempts": 1,
            "runtime_digest": engine.runtime_digest,
            "handoff_digest": handoff_digest,
        },
    }


def build_candidate_training_receipt(
    handoff: Mapping[str, Any],
    *,
    model_digest: str,
    execution_receipt_digest: str,
) -> dict[str, Any]:
    """Extend the governed handoff lineage for one successful offline ReOPD run."""

    if not isinstance(handoff, Mapping) or handoff.get("contract") != CONTRACT:
        raise GovernanceError("handoff must use the governed model-factory contract")
    pep = handoff.get("pep_handoff")
    if not isinstance(pep, Mapping):
        raise GovernanceError("handoff is missing pep_handoff")
    handoff_digest = _require_digest(
        pep.get("handoff_digest"), "pep_handoff.handoff_digest"
    )
    core = dict(handoff)
    core.pop("pep_handoff", None)
    if digest(core) != handoff_digest:
        raise GovernanceError("pep handoff digest does not match governed handoff")
    training_spec = handoff.get("training_spec")
    if not isinstance(training_spec, Mapping):
        raise GovernanceError("handoff training_spec is invalid")
    recipe = training_spec.get("recipe")
    if not isinstance(recipe, Mapping) or recipe.get("name") != "reopd":
        raise GovernanceError("candidate training receipt requires a validated ReOPD recipe")
    if (
        recipe.get("output_standing") != "candidate_only"
        or recipe.get("inherits_teacher_authority") is not False
        or recipe.get("inherits_teacher_capability") is not False
    ):
        raise GovernanceError("ReOPD output standing or inheritance controls are invalid")
    resolved_model_digest = _require_digest(model_digest, "model_digest")
    resolved_execution_receipt = _require_digest(
        execution_receipt_digest, "execution_receipt_digest"
    )
    accepted = recipe.get("accepted_trajectories")
    if not isinstance(accepted, list) or not accepted:
        raise GovernanceError("validated ReOPD trajectories are missing")

    body = {
        "contract": CONTRACT,
        "training_status": "SUCCEEDED",
        "pep_handoff_digest": handoff_digest,
        "execution_receipt_digest": resolved_execution_receipt,
        "engine": dict(handoff.get("engine", {})),
        "recipe": "reopd",
        "dataset_digest": _require_digest(
            training_spec.get("dataset_digest"), "training_spec.dataset_digest"
        ),
        "base_model_digest": _require_digest(
            recipe.get("base_model_digest"), "recipe.base_model_digest"
        ),
        "model_digest": resolved_model_digest,
        "trajectory_digests": [item["trajectory_digest"] for item in accepted],
        "trajectory_provenance_receipt_digests": [
            item["provenance_receipt_digest"] for item in accepted
        ],
        "trajectory_admission_receipt_digests": [
            item["admission_receipt_digest"] for item in accepted
        ],
        "teacher": dict(recipe.get("teacher", {})),
        "prefix_sampling": dict(recipe.get("prefix_sampling", {})),
        "distribution_shift_measurements": list(
            recipe.get("distribution_shift_measurements", [])
        ),
        "output": {
            "standing": "CANDIDATE_ONLY",
            "runtime_authority": False,
            "runtime_capabilities": [],
            "inherits_teacher_authority": False,
            "inherits_teacher_capability": False,
        },
        "promotion": {
            "automatic": False,
            "required_gates": list(CANDIDATE_PROMOTION_GATES),
            "requires_new_admission": True,
        },
    }
    return {**body, "training_receipt_digest": digest(body)}


def build_unsloth_request(
    *,
    workspace: Mapping[str, Any],
    state_admission: Mapping[str, Any],
    governance: Sequence[Mapping[str, Any]],
    training_spec: Mapping[str, Any],
    runtime_digest: str,
    attestor: str,
    attestation_receipt_digest: str,
    external_adapter: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a request pinned to the current VALO Unsloth fork commit."""

    engine = EngineRef.pinned_unsloth(
        runtime_digest=runtime_digest,
        attestor=attestor,
        attestation_receipt_digest=attestation_receipt_digest,
    )
    return {
        "workspace": dict(workspace),
        "state_admission": dict(state_admission),
        "engine": engine.identity(),
        "governance": [dict(item) for item in governance],
        "training_spec": dict(training_spec),
        "attempt": 1,
        "auto_promote": False,
        "authority_sources": ["workspace_authority"],
        "external_adapter": dict(external_adapter) if external_adapter else None,
    }
