from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from veritas.contracts import ObservationPackageV1, ObservedEventV1
from veritas.digest import canonical_digest

_SCHEMA = "heimel.consequence.outcome-observation.v1"
_ALLOWED_FIELDS = frozenset(
    {
        "schema",
        "consequence_id",
        "execution_id",
        "gateway_record_id",
        "action_digest",
        "completion_criteria_hash",
        "evidence_requirement_hash",
        "governed_effect_completed",
        "completion_criteria_satisfied",
        "required_evidence_verified",
        "verified_at",
        "verifier_id",
        "verifier_version",
        "verifier_config_digest",
        "authority_granted",
        "observation_digest",
    }
)
_HEX = set("0123456789abcdef")


class ConsequenceOutcomeObservationError(ValueError):
    pass


def _require_text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise ConsequenceOutcomeObservationError(f"{name} is required")
    return value


def _require_digest(name: str, value: Any, *, prefixed: bool = True) -> str:
    text = _require_text(name, value)
    raw = text[7:] if text.startswith("sha256:") else text
    if prefixed and not text.startswith("sha256:"):
        raise ConsequenceOutcomeObservationError(f"{name} must use sha256: prefix")
    if len(raw) != 64 or any(char not in _HEX for char in raw):
        raise ConsequenceOutcomeObservationError(f"{name} must be a sha256 digest")
    return text


def _require_timestamp(name: str, value: Any) -> str:
    text = _require_text(name, value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ConsequenceOutcomeObservationError(f"{name} must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ConsequenceOutcomeObservationError(f"{name} must be timezone-aware")
    return text


@dataclass(frozen=True)
class ConsequenceOutcomeObservationV1:
    """Non-authoritative observation of consequence verification output.

    The exact verifier implementation is bound by identity, version and
    configuration digest. Veritas preserves the verifier's result but neither
    grants authority nor decides whether completion criteria are satisfied.
    """

    payload: Mapping[str, Any]

    @classmethod
    def verify(cls, payload: Mapping[str, Any]) -> "ConsequenceOutcomeObservationV1":
        data = dict(payload)
        if data.get("schema") != _SCHEMA:
            raise ConsequenceOutcomeObservationError(
                "unsupported consequence outcome observation schema"
            )
        unexpected = set(data).difference(_ALLOWED_FIELDS)
        if unexpected:
            raise ConsequenceOutcomeObservationError(
                "unexpected consequence outcome fields: " + ", ".join(sorted(unexpected))
            )
        if data.get("authority_granted") is not False:
            raise ConsequenceOutcomeObservationError(
                "Veritas consequence observation must never grant authority"
            )

        for name in (
            "consequence_id",
            "execution_id",
            "gateway_record_id",
            "verifier_id",
            "verifier_version",
        ):
            _require_text(name, data.get(name))
        _require_digest("verifier_config_digest", data.get("verifier_config_digest"))
        _require_digest("action_digest", data.get("action_digest"), prefixed=False)
        for name in ("completion_criteria_hash", "evidence_requirement_hash"):
            _require_digest(name, data.get(name))
        _require_timestamp("verified_at", data.get("verified_at"))
        for name in (
            "governed_effect_completed",
            "completion_criteria_satisfied",
            "required_evidence_verified",
        ):
            if not isinstance(data.get(name), bool):
                raise ConsequenceOutcomeObservationError(f"{name} must be boolean")
        _require_digest("observation_digest", data.get("observation_digest"))

        claimed = data.pop("observation_digest")
        if claimed != canonical_digest(data):
            raise ConsequenceOutcomeObservationError(
                "consequence outcome observation digest mismatch"
            )
        return cls(payload=dict(payload))

    def to_observed_event(self) -> ObservedEventV1:
        data = dict(self.payload)
        return ObservedEventV1(
            event_id=f"outcome:{data['consequence_id']}",
            source_id=data["verifier_id"],
            event_type="consequence_outcome_verified",
            observed_at=datetime.fromisoformat(data["verified_at"].replace("Z", "+00:00")),
            payload_digest=data["observation_digest"],
            provenance={
                "authority_granted": False,
                "consequence_id": data["consequence_id"],
                "execution_id": data["execution_id"],
                "gateway_record_id": data["gateway_record_id"],
                "action_digest": data["action_digest"],
                "completion_criteria_hash": data["completion_criteria_hash"],
                "evidence_requirement_hash": data["evidence_requirement_hash"],
                "governed_effect_completed": data["governed_effect_completed"],
                "completion_criteria_satisfied": data["completion_criteria_satisfied"],
                "required_evidence_verified": data["required_evidence_verified"],
                "verifier_id": data["verifier_id"],
                "verifier_version": data["verifier_version"],
                "verifier_config_digest": data["verifier_config_digest"],
            },
        )

    def to_observation_package(self, *, tenant_id: str) -> ObservationPackageV1:
        data = dict(self.payload)
        _require_text("tenant_id", tenant_id)
        event = self.to_observed_event()
        return ObservationPackageV1(
            package_id=f"outcome:{data['consequence_id']}",
            tenant_id=tenant_id,
            execution_id=data["execution_id"],
            authorization_ref=f"gateway-record:{data['gateway_record_id']}",
            authorization_digest=(
                data["action_digest"]
                if data["action_digest"].startswith("sha256:")
                else "sha256:" + data["action_digest"]
            ),
            handoff_ref=(
                f"consequence-verifier:{data['verifier_id']}@{data['verifier_version']}"
            ),
            handoff_digest=data["verifier_config_digest"],
            observed_events=(event,),
            created_at=datetime.fromisoformat(data["verified_at"].replace("Z", "+00:00")),
        )


def consequence_outcome_digest(payload_without_digest: Mapping[str, Any]) -> str:
    return canonical_digest(dict(payload_without_digest))


__all__ = [
    "ConsequenceOutcomeObservationError",
    "ConsequenceOutcomeObservationV1",
    "consequence_outcome_digest",
]
