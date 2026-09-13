"""Bind VAIG coherence evaluation into the downstream REHT handoff packet.

The binding is evidence, not authority. A handoff-ready binding requires a
coherence PASS, but PASS still cannot execute anything: REHT remains the sole
execution-authority owner.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from vaig.coherence_evaluation import CoherenceEvaluationResultV1, EvaluationStatus


COHERENCE_EVIDENCE_KEY = "vaig_coherence_evaluation"
BINDING_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class CoherenceHandoffBindingV1:
    """Digest-bound VAIG evaluation evidence for a REHT-bound packet."""

    result: dict[str, Any]
    result_digest: str
    schema_version: str = BINDING_SCHEMA_VERSION
    execution_authority: bool = False
    requires_reht_clearance: bool = True
    can_execute: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != BINDING_SCHEMA_VERSION:
            raise ValueError("unsupported coherence handoff binding schema_version")
        if self.execution_authority:
            raise ValueError("coherence handoff binding cannot grant execution authority")
        if not self.requires_reht_clearance:
            raise ValueError("coherence handoff binding must require REHT clearance")
        if self.can_execute:
            raise ValueError("coherence handoff binding can never be executable")
        expected = _digest(self.result)
        if self.result_digest != expected:
            raise ValueError("coherence handoff result_digest mismatch")

    @classmethod
    def from_result(cls, result: CoherenceEvaluationResultV1) -> "CoherenceHandoffBindingV1":
        payload = result.canonical_payload()
        return cls(result=payload, result_digest=_digest(payload))

    @property
    def status(self) -> EvaluationStatus:
        return EvaluationStatus(self.result["status"])

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "result": dict(self.result),
            "result_digest": self.result_digest,
            "execution_authority": False,
            "requires_reht_clearance": True,
            "can_execute": False,
        }


def bind_coherence_result(
    packet: Mapping[str, Any],
    result: CoherenceEvaluationResultV1,
    *,
    require_pass: bool = True,
) -> dict[str, Any]:
    """Return a packet copy with the VAIG coherence result bound into evidence.

    Handoff construction is fail-closed by default: OPEN/FAIL results cannot be
    promoted into a REHT-bound execution packet. Set ``require_pass=False`` only
    when constructing an audit/blocked packet that will not cross the effect
    boundary.
    """

    if require_pass and result.status is not EvaluationStatus.PASS:
        raise ValueError(
            f"coherence evaluation must PASS before REHT handoff; got {result.status.value}"
        )

    bound = copy.deepcopy(dict(packet))
    evidence = bound.setdefault("evidence", {})
    if not isinstance(evidence, dict):
        raise ValueError("packet evidence must be an object")

    evidence[COHERENCE_EVIDENCE_KEY] = CoherenceHandoffBindingV1.from_result(
        result
    ).canonical_payload()
    return bound


def read_coherence_binding(packet: Mapping[str, Any]) -> CoherenceHandoffBindingV1 | None:
    """Parse and validate the coherence binding from a packet, if present."""

    evidence = packet.get("evidence", {})
    if not isinstance(evidence, Mapping):
        raise ValueError("packet evidence must be an object")
    raw = evidence.get(COHERENCE_EVIDENCE_KEY)
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise ValueError("coherence handoff binding must be an object")

    return CoherenceHandoffBindingV1(
        result=dict(raw.get("result", {})),
        result_digest=str(raw.get("result_digest", "")),
        schema_version=str(raw.get("schema_version", "")),
        execution_authority=bool(raw.get("execution_authority", False)),
        requires_reht_clearance=bool(raw.get("requires_reht_clearance", False)),
        can_execute=bool(raw.get("can_execute", False)),
    )


def _digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()
