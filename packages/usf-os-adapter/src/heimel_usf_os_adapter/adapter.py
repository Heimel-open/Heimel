from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping


ALLOWED_EVIDENCE_CLASSES = {"OBSERVED", "MEASURED", "INFERRED", "MODELED", "DECIDED"}
REQUIRED_PACKET_FIELDS = {
    "object",
    "boundary",
    "evidence",
    "unit",
    "current_state",
    "required_state",
    "gap",
    "residual_owner",
    "closure_gate",
    "replay",
}
ALLOWED_PACKET_FIELDS = REQUIRED_PACKET_FIELDS | {"clocks", "actors"}
ALLOWED_EVIDENCE_FIELDS = {"class", "source_ref", "observed_at"}
ALLOWED_CLOCK_FIELDS = {"awareness", "duty", "action", "resolution"}
ALLOWED_ACTOR_FIELDS = {"operator", "second_operator", "signer"}
FORBIDDEN_EXTERNAL_SEMANTICS = {
    "authority",
    "authority_snapshot",
    "permit",
    "decision",
    "effect",
    "effect_class",
    "consequence",
    "consequence_bearing",
    "tool",
    "tool_id",
    "allow",
    "deny",
    "escalate",
}


class AdapterReject(ValueError):
    """Fail-closed rejection before any external packet can reach Heimel runtime semantics."""


@dataclass(frozen=True)
class AdapterResult:
    source_system: str
    source_version: str
    canonical: dict[str, Any]
    admission: dict[str, str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "adapter": "heimel.usf_os.v1",
            "external_source": {
                "system": self.source_system,
                "version": self.source_version,
            },
            "canonical": self.canonical,
            "admission": self.admission,
        }


def _require_nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AdapterReject(f"{field} must be a non-empty string")
    return value.strip()


def _reject_unknown_keys(value: Mapping[str, Any], allowed: set[str], where: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise AdapterReject(f"unknown {where} fields: {', '.join(sorted(unknown))}")


def _validate_iso_timestamp(value: Any, field: str) -> str:
    timestamp = _require_nonempty_string(value, field)
    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AdapterReject(f"{field} must be ISO-8601") from exc
    return timestamp


def _validate_json_value(value: Any, field: str) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_validate_json_value(item, field) for item in value]
    if isinstance(value, Mapping):
        return {
            _require_nonempty_string(key, f"{field} key"): _validate_json_value(item, field)
            for key, item in value.items()
        }
    raise AdapterReject(f"{field} contains a non-canonical value type")


def map_usf_os_packet(envelope: Mapping[str, Any]) -> AdapterResult:
    """Map a USF-OS packet into a non-authoritative Heimel ingress contract.

    This function never creates authority, an effect classification, a permit, or an
    execution decision. Those semantics remain unresolved until Heimel resolves them
    from its own authoritative state at consequence time.
    """
    if not isinstance(envelope, Mapping):
        raise AdapterReject("envelope must be an object")

    _reject_unknown_keys(envelope, {"source_system", "source_version", "packet"}, "envelope")
    if set(envelope) != {"source_system", "source_version", "packet"}:
        missing = {"source_system", "source_version", "packet"} - set(envelope)
        raise AdapterReject(f"missing envelope fields: {', '.join(sorted(missing))}")

    source_system = _require_nonempty_string(envelope["source_system"], "source_system")
    if source_system != "USF-OS":
        raise AdapterReject("source_system must be USF-OS")
    source_version = _require_nonempty_string(envelope["source_version"], "source_version")

    packet = envelope["packet"]
    if not isinstance(packet, Mapping):
        raise AdapterReject("packet must be an object")

    forbidden = set(packet) & FORBIDDEN_EXTERNAL_SEMANTICS
    if forbidden:
        raise AdapterReject(
            "external packet attempted to supply governed semantics: "
            + ", ".join(sorted(forbidden))
        )

    _reject_unknown_keys(packet, ALLOWED_PACKET_FIELDS, "packet")
    missing = REQUIRED_PACKET_FIELDS - set(packet)
    if missing:
        raise AdapterReject(f"missing packet fields: {', '.join(sorted(missing))}")

    evidence = packet["evidence"]
    if not isinstance(evidence, Mapping):
        raise AdapterReject("evidence must be an object")
    _reject_unknown_keys(evidence, ALLOWED_EVIDENCE_FIELDS, "evidence")
    if set(evidence) != ALLOWED_EVIDENCE_FIELDS:
        missing_evidence = ALLOWED_EVIDENCE_FIELDS - set(evidence)
        raise AdapterReject(f"missing evidence fields: {', '.join(sorted(missing_evidence))}")

    evidence_class = _require_nonempty_string(evidence["class"], "evidence.class").upper()
    if evidence_class == "OPEN":
        raise AdapterReject("OPEN evidence cannot enter the governed path")
    if evidence_class not in ALLOWED_EVIDENCE_CLASSES:
        raise AdapterReject("unsupported evidence class")

    source_ref = _require_nonempty_string(evidence["source_ref"], "evidence.source_ref")
    observed_at = _validate_iso_timestamp(evidence["observed_at"], "evidence.observed_at")

    replay = packet["replay"]
    if replay is not True and replay != "required":
        raise AdapterReject("replay must be required")

    clocks: dict[str, str] = {}
    if "clocks" in packet:
        raw_clocks = packet["clocks"]
        if not isinstance(raw_clocks, Mapping):
            raise AdapterReject("clocks must be an object")
        _reject_unknown_keys(raw_clocks, ALLOWED_CLOCK_FIELDS, "clock")
        clocks = {
            key: _validate_iso_timestamp(value, f"clocks.{key}")
            for key, value in raw_clocks.items()
        }

    actors: dict[str, str] = {}
    if "actors" in packet:
        raw_actors = packet["actors"]
        if not isinstance(raw_actors, Mapping):
            raise AdapterReject("actors must be an object")
        _reject_unknown_keys(raw_actors, ALLOWED_ACTOR_FIELDS, "actor")
        actors = {
            key: _require_nonempty_string(value, f"actors.{key}")
            for key, value in raw_actors.items()
        }

    canonical = {
        "subject": {
            "external_object": _validate_json_value(packet["object"], "object"),
            "boundary": _validate_json_value(packet["boundary"], "boundary"),
        },
        "state": {
            "current": _validate_json_value(packet["current_state"], "current_state"),
            "required": _validate_json_value(packet["required_state"], "required_state"),
            "gap": _validate_json_value(packet["gap"], "gap"),
        },
        "evidence_input": {
            "class": evidence_class,
            "source_ref": source_ref,
            "observed_at": observed_at,
            "status": "EXTERNAL_UNVERIFIED",
        },
        "measurement": {
            "unit": _require_nonempty_string(packet["unit"], "unit"),
            "clocks": clocks,
        },
        "responsibility": {
            "residual_owner_ref": _require_nonempty_string(
                packet["residual_owner"], "residual_owner"
            ),
            "actor_refs": actors,
            "status": "EXTERNAL_REFERENCES_ONLY",
        },
        "constraints": {
            "closure_gate": _validate_json_value(packet["closure_gate"], "closure_gate"),
        },
        "replay": {"required": True},
    }

    return AdapterResult(
        source_system=source_system,
        source_version=source_version,
        canonical=canonical,
        admission={
            "status": "MAPPED_NOT_AUTHORIZED",
            "authority": "UNRESOLVED",
            "effect": "UNRESOLVED",
            "evidence": "REQUIRES_HEIMEL_VERIFICATION",
        },
    )
