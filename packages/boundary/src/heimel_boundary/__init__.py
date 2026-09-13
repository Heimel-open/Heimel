"""Small, local-only reference for Heimel's consequence boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
from typing import Callable


class BoundaryError(RuntimeError):
    """Raised when a permit cannot be used for the exact effect."""


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class Effect:
    effect_id: str
    actor_id: str
    action: str
    target: str

    @property
    def digest(self) -> str:
        return _digest(self.__dict__)


@dataclass(frozen=True)
class Permit:
    permit_id: str
    effect_digest: str
    state_revision: int
    expires_at: datetime


@dataclass(frozen=True)
class Receipt:
    receipt_id: str
    permit_id: str
    effect_digest: str
    state_revision: int
    outcome: str
    receipt_digest: str


class ReferenceBoundary:
    """In-memory demonstration; it never calls an external system."""

    def __init__(self) -> None:
        self.state_revision = 1
        self._allowed: set[str] = set()
        self._consumed: set[str] = set()

    def allow(self, effect: Effect) -> None:
        """Configure the local demo authority state."""
        self._allowed.add(effect.digest)

    def revoke(self, effect: Effect) -> None:
        self._allowed.discard(effect.digest)
        self.state_revision += 1

    def authorize(self, effect: Effect, *, now: datetime) -> Permit:
        if effect.digest not in self._allowed:
            raise BoundaryError("authority denied for exact effect")
        return Permit(
            permit_id=_digest({"effect": effect.digest, "revision": self.state_revision}),
            effect_digest=effect.digest,
            state_revision=self.state_revision,
            expires_at=now + timedelta(seconds=30),
        )

    def execute(
        self,
        permit: Permit,
        effect: Effect,
        *,
        now: datetime,
        local_effect: Callable[[Effect], str],
    ) -> Receipt:
        if permit.permit_id in self._consumed:
            raise BoundaryError("one-shot permit already consumed")
        if permit.effect_digest != effect.digest:
            raise BoundaryError("permit is not bound to exact effect")
        if permit.state_revision != self.state_revision:
            raise BoundaryError("authority state is stale")
        if now.tzinfo is None or now >= permit.expires_at:
            raise BoundaryError("permit expired")
        self._consumed.add(permit.permit_id)
        outcome = local_effect(effect)
        receipt_body = {
            "permit_id": permit.permit_id,
            "effect_digest": effect.digest,
            "state_revision": self.state_revision,
            "outcome": outcome,
        }
        return Receipt(
            receipt_id=_digest(receipt_body),
            permit_id=permit.permit_id,
            effect_digest=effect.digest,
            state_revision=self.state_revision,
            outcome=outcome,
            receipt_digest=_digest(receipt_body),
        )


__all__ = ["BoundaryError", "Effect", "Permit", "Receipt", "ReferenceBoundary"]
