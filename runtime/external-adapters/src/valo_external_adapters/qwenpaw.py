"""QwenPaw/AgentScope adapter for Heimel consequence-time authorization.

External QwenPaw mission, worker, approval, tool, and payload data is treated as
untrusted input. The adapter maps it into a canonical effect binding, resolves
fresh authority at consequence time, issues a one-shot permit only on an exact
match, and emits hash-chained Veritas-style decision evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from hashlib import sha256
import json
import secrets
from typing import Any, Mapping, Protocol


class QwenPawAdapterError(RuntimeError):
    """Base adapter error."""


class UnknownEffect(QwenPawAdapterError):
    """Raised when QwenPaw requests an effect not registered by Heimel."""


class PermitRejected(QwenPawAdapterError):
    """Raised when a denied or invalid permit would otherwise reach a driver."""


@dataclass(frozen=True)
class QwenPawEffectMetadata:
    tool_name: str
    effect_type: str
    canonical_effect: str
    consequence_bearing: bool = True


@dataclass(frozen=True)
class QwenPawMissionEffect:
    mission_id: str
    worker_id: str
    source: str
    tool_name: str
    effect_type: str
    resource: str
    payload: Mapping[str, Any]
    approval_authority_digest: str
    approval_id: str


@dataclass(frozen=True)
class AuthoritySnapshot:
    authority_digest: str
    state_digest: str
    allowed_effects: frozenset[str]
    observed_at: str


@dataclass(frozen=True)
class ConsequenceBinding:
    mission_id: str
    worker_id: str
    source: str
    canonical_effect: str
    resource: str
    payload_digest: str
    authority_digest: str
    state_digest: str

    @property
    def digest(self) -> str:
        return _digest(asdict(self))


@dataclass(frozen=True)
class OneShotPermit:
    permit_id: str
    binding_digest: str
    authority_digest: str
    state_digest: str


@dataclass(frozen=True)
class VeritasReceipt:
    receipt_id: str
    sequence: int
    previous_hash: str | None
    record_hash: str
    record: Mapping[str, Any]


@dataclass(frozen=True)
class AdapterDecision:
    allowed: bool
    reason: str
    binding: ConsequenceBinding | None
    permit: OneShotPermit | None
    receipt: VeritasReceipt
    driver_result: Any = None


class AuthorityResolver(Protocol):
    def __call__(self, effect: QwenPawMissionEffect) -> AuthoritySnapshot: ...


class EffectDriver(Protocol):
    def __call__(self, binding: ConsequenceBinding) -> Any: ...


class InMemoryVeritasChain:
    """Deterministic append-only evidence chain for adapter demos/tests."""

    def __init__(self) -> None:
        self._receipts: list[VeritasReceipt] = []

    @property
    def receipts(self) -> tuple[VeritasReceipt, ...]:
        return tuple(self._receipts)

    def append(self, record: Mapping[str, Any]) -> VeritasReceipt:
        previous_hash = self._receipts[-1].record_hash if self._receipts else None
        sequence = len(self._receipts) + 1
        canonical = {
            "sequence": sequence,
            "previous_hash": previous_hash,
            "record": _jsonable(record),
        }
        record_hash = _digest(canonical)
        receipt = VeritasReceipt(
            receipt_id=f"veritas-{sequence}-{record_hash[:16]}",
            sequence=sequence,
            previous_hash=previous_hash,
            record_hash=record_hash,
            record=dict(record),
        )
        self._receipts.append(receipt)
        return receipt

    def verify(self) -> bool:
        previous_hash: str | None = None
        for index, receipt in enumerate(self._receipts, start=1):
            canonical = {
                "sequence": index,
                "previous_hash": previous_hash,
                "record": _jsonable(receipt.record),
            }
            if receipt.sequence != index or receipt.previous_hash != previous_hash:
                return False
            if receipt.record_hash != _digest(canonical):
                return False
            previous_hash = receipt.record_hash
        return True


class QwenPawEffectRegistry:
    """Runtime-owned effect classification; caller fields cannot override it."""

    def __init__(self, effects: list[QwenPawEffectMetadata] | tuple[QwenPawEffectMetadata, ...]):
        self._effects = {(item.tool_name, item.effect_type): item for item in effects}

    def resolve(self, tool_name: str, effect_type: str) -> QwenPawEffectMetadata:
        try:
            return self._effects[(tool_name, effect_type)]
        except KeyError as exc:
            raise UnknownEffect(f"unregistered effect: {tool_name}:{effect_type}") from exc


class HeimelQwenPawAdapter:
    """Single governed path from QwenPaw mission effects to consequence drivers."""

    def __init__(
        self,
        *,
        registry: QwenPawEffectRegistry,
        authority_resolver: AuthorityResolver,
        veritas: InMemoryVeritasChain,
    ) -> None:
        self._registry = registry
        self._authority_resolver = authority_resolver
        self._veritas = veritas
        self._unconsumed: dict[str, OneShotPermit] = {}

    def execute(self, effect: QwenPawMissionEffect, driver: EffectDriver) -> AdapterDecision:
        try:
            metadata = self._registry.resolve(effect.tool_name, effect.effect_type)
        except UnknownEffect:
            receipt = self._record(effect, False, "UNKNOWN_EFFECT_FAIL_CLOSED", None, None)
            return AdapterDecision(False, "UNKNOWN_EFFECT_FAIL_CLOSED", None, None, receipt)

        if not metadata.consequence_bearing:
            receipt = self._record(effect, False, "NON_CONSEQUENCE_EFFECT_NOT_ADMITTED", None, None)
            return AdapterDecision(False, "NON_CONSEQUENCE_EFFECT_NOT_ADMITTED", None, None, receipt)

        fresh = self._authority_resolver(effect)
        binding = ConsequenceBinding(
            mission_id=effect.mission_id,
            worker_id=effect.worker_id,
            source=effect.source,
            canonical_effect=metadata.canonical_effect,
            resource=effect.resource,
            payload_digest=_digest(effect.payload),
            authority_digest=fresh.authority_digest,
            state_digest=fresh.state_digest,
        )

        if effect.approval_authority_digest != fresh.authority_digest:
            receipt = self._record(effect, False, "STALE_AUTHORITY", binding, None)
            return AdapterDecision(False, "STALE_AUTHORITY", binding, None, receipt)

        if metadata.canonical_effect not in fresh.allowed_effects:
            receipt = self._record(effect, False, "EFFECT_NOT_AUTHORIZED", binding, None)
            return AdapterDecision(False, "EFFECT_NOT_AUTHORIZED", binding, None, receipt)

        permit = OneShotPermit(
            permit_id=f"qwp-{secrets.token_hex(12)}",
            binding_digest=binding.digest,
            authority_digest=fresh.authority_digest,
            state_digest=fresh.state_digest,
        )
        self._unconsumed[permit.permit_id] = permit
        admit_receipt = self._record(effect, True, "ALLOW", binding, permit)
        result = self._consume_and_execute(effect, binding, permit, driver)
        return AdapterDecision(True, "ALLOW", binding, permit, admit_receipt, result)

    def _consume_and_execute(
        self,
        effect: QwenPawMissionEffect,
        binding: ConsequenceBinding,
        permit: OneShotPermit,
        driver: EffectDriver,
    ) -> Any:
        stored = self._unconsumed.pop(permit.permit_id, None)
        if stored is None:
            self._record(effect, False, "PERMIT_REPLAY", binding, permit)
            raise PermitRejected("permit already consumed or unknown")
        if stored.binding_digest != binding.digest:
            self._record(effect, False, "PERMIT_BINDING_MISMATCH", binding, permit)
            raise PermitRejected("permit binding mismatch")

        fresh = self._authority_resolver(effect)
        if fresh.authority_digest != permit.authority_digest or fresh.state_digest != permit.state_digest:
            self._record(effect, False, "AUTHORITY_CHANGED_BEFORE_EFFECT", binding, permit)
            raise PermitRejected("authority/state changed before effect")

        result = driver(binding)
        self._record(effect, True, "EFFECT_COMMITTED", binding, permit)
        return result

    def _record(
        self,
        effect: QwenPawMissionEffect,
        allowed: bool,
        reason: str,
        binding: ConsequenceBinding | None,
        permit: OneShotPermit | None,
    ) -> VeritasReceipt:
        return self._veritas.append(
            {
                "adapter": "qwenpaw",
                "mission_id": effect.mission_id,
                "worker_id": effect.worker_id,
                "source": effect.source,
                "tool_name": effect.tool_name,
                "effect_type": effect.effect_type,
                "approval_id": effect.approval_id,
                "approval_authority_digest": effect.approval_authority_digest,
                "allowed": allowed,
                "reason": reason,
                "binding_digest": binding.digest if binding else None,
                "fresh_authority_digest": binding.authority_digest if binding else None,
                "fresh_state_digest": binding.state_digest if binding else None,
                "permit_id": permit.permit_id if permit else None,
            }
        )


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted(_jsonable(item) for item in value)
    return value


def _digest(value: Any) -> str:
    payload = json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(payload.encode("utf-8")).hexdigest()
