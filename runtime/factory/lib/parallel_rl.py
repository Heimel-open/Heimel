"""Governed Parallel-RL capability composition.

This module validates capability lineage and emits a candidate-only composition
manifest. It does not train, merge, promote, deploy, or grant authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

CONTRACT = "valo.parallel-rl-composition.v1"
STRATEGY = "parallel_rl"
HEX64 = re.compile(r"^[0-9a-f]{64}$")

AUTHORITY_FIELDS = {
    "authority",
    "authority_ref",
    "authority_receipt",
    "authority_receipt_digest",
    "authorized",
    "grants_authority",
    "execution_authority",
}


class ParallelRLError(ValueError):
    """Raised when a Parallel-RL composition request is not admissible."""


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
        raise ParallelRLError(f"{field} must be a non-empty string")
    return value.strip()


def _require_digest(value: Any, field: str) -> str:
    text = _require_text(value, field).lower()
    if not HEX64.fullmatch(text):
        raise ParallelRLError(f"{field} must be a lowercase sha256 digest")
    return text


def _reject_authority_fields(value: Mapping[str, Any], field: str) -> None:
    overlap = AUTHORITY_FIELDS.intersection(value.keys())
    if overlap:
        raise ParallelRLError(
            f"{field} contains forbidden authority fields: "
            + ", ".join(sorted(overlap))
        )


@dataclass(frozen=True)
class CapabilityCandidate:
    capability_id: str
    version: str
    base_model_digest: str
    dataset_digest: str
    reward_spec_digest: str
    delta_digest: str
    evaluation_receipt_digests: tuple[str, ...]
    negative_test_receipt_digest: str
    compatibility_receipt_digest: str
    status: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any], index: int) -> "CapabilityCandidate":
        field = f"capabilities[{index}]"
        _reject_authority_fields(value, field)
        status = _require_text(value.get("status"), f"{field}.status").upper()
        if status != "EVALUATED_CANDIDATE":
            raise ParallelRLError(
                f"{field}.status must be EVALUATED_CANDIDATE before composition"
            )
        receipts_raw = value.get("evaluation_receipt_digests")
        if not isinstance(receipts_raw, list) or not receipts_raw:
            raise ParallelRLError(
                f"{field}.evaluation_receipt_digests must be a non-empty list"
            )
        receipts = tuple(
            _require_digest(item, f"{field}.evaluation_receipt_digests[{receipt_index}]")
            for receipt_index, item in enumerate(receipts_raw)
        )
        return cls(
            capability_id=_require_text(value.get("capability_id"), f"{field}.capability_id"),
            version=_require_text(value.get("version"), f"{field}.version"),
            base_model_digest=_require_digest(
                value.get("base_model_digest"), f"{field}.base_model_digest"
            ),
            dataset_digest=_require_digest(
                value.get("dataset_digest"), f"{field}.dataset_digest"
            ),
            reward_spec_digest=_require_digest(
                value.get("reward_spec_digest"), f"{field}.reward_spec_digest"
            ),
            delta_digest=_require_digest(value.get("delta_digest"), f"{field}.delta_digest"),
            evaluation_receipt_digests=receipts,
            negative_test_receipt_digest=_require_digest(
                value.get("negative_test_receipt_digest"),
                f"{field}.negative_test_receipt_digest",
            ),
            compatibility_receipt_digest=_require_digest(
                value.get("compatibility_receipt_digest"),
                f"{field}.compatibility_receipt_digest",
            ),
            status=status,
        )

    def normalized(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "version": self.version,
            "base_model_digest": self.base_model_digest,
            "dataset_digest": self.dataset_digest,
            "reward_spec_digest": self.reward_spec_digest,
            "delta_digest": self.delta_digest,
            "evaluation_receipt_digests": list(self.evaluation_receipt_digests),
            "negative_test_receipt_digest": self.negative_test_receipt_digest,
            "compatibility_receipt_digest": self.compatibility_receipt_digest,
            "status": self.status,
        }


def validate_capabilities(
    capabilities: Sequence[Mapping[str, Any]],
) -> tuple[CapabilityCandidate, ...]:
    if len(capabilities) < 2:
        raise ParallelRLError("Parallel-RL composition requires at least two capabilities")

    parsed = tuple(
        CapabilityCandidate.from_mapping(value, index)
        for index, value in enumerate(capabilities)
    )

    base_digests = {item.base_model_digest for item in parsed}
    if len(base_digests) != 1:
        raise ParallelRLError("all capabilities must share the same base_model_digest")

    capability_ids = [item.capability_id for item in parsed]
    if len(set(capability_ids)) != len(capability_ids):
        raise ParallelRLError("capability_id values must be unique")

    delta_digests = [item.delta_digest for item in parsed]
    if len(set(delta_digests)) != len(delta_digests):
        raise ParallelRLError("delta_digest values must be unique")

    return parsed


def build_composition_candidate(request: Mapping[str, Any]) -> dict[str, Any]:
    """Return a deterministic candidate-only composition manifest."""

    if not isinstance(request, Mapping):
        raise ParallelRLError("request must be an object")
    _reject_authority_fields(request, "request")

    strategy = _require_text(request.get("strategy", STRATEGY), "strategy").lower()
    if strategy != STRATEGY:
        raise ParallelRLError("strategy must be parallel_rl")

    if request.get("auto_promote") not in (None, False):
        raise ParallelRLError("automatic promotion is forbidden")

    capabilities_raw = request.get("capabilities")
    if not isinstance(capabilities_raw, list):
        raise ParallelRLError("capabilities must be a list")
    if any(not isinstance(item, Mapping) for item in capabilities_raw):
        raise ParallelRLError("each capability must be an object")

    capabilities = validate_capabilities(capabilities_raw)
    composition_id = _require_text(request.get("composition_id"), "composition_id")
    purpose_id = _require_text(request.get("purpose_id"), "purpose_id")
    target_model_name = _require_text(
        request.get("target_model_name"), "target_model_name"
    )
    composition_evaluation_plan_digest = _require_digest(
        request.get("composition_evaluation_plan_digest"),
        "composition_evaluation_plan_digest",
    )

    core = {
        "contract": CONTRACT,
        "strategy": STRATEGY,
        "composition_id": composition_id,
        "purpose_id": purpose_id,
        "target_model_name": target_model_name,
        "base_model_digest": capabilities[0].base_model_digest,
        "capabilities": [item.normalized() for item in capabilities],
        "composition_evaluation_plan_digest": composition_evaluation_plan_digest,
        "composition_status": "CANDIDATE_REQUIRES_EVALUATION",
        "promotion": {
            "mode": "candidate_only",
            "automatic": False,
            "requires_new_admission": True,
        },
        "authority": {
            "granted": False,
            "source": "none",
            "execution_authority_required_at_runtime": True,
        },
    }
    return {**core, "composition_digest": digest(core)}
