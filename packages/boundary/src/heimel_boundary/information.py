"""Governed information lifecycle before consequence-time authorization.

This boundary governs admission, bounded use, derivative lineage, controlled
egress, state admission, and explicit closure. It does not replace Heimel's
fresh-authority and exact-effect consequence boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
from typing import Iterable


class InformationBoundaryError(RuntimeError):
    """Raised when an information lifecycle transition is not authorized."""


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class InformationObject:
    object_id: str
    authority_id: str
    content_digest: str
    classification: str = "INTERNAL"
    parent_digests: tuple[str, ...] = ()

    @classmethod
    def from_payload(
        cls,
        object_id: str,
        authority_id: str,
        payload: object,
        *,
        classification: str = "INTERNAL",
        parent_digests: Iterable[str] = (),
    ) -> "InformationObject":
        return cls(
            object_id=object_id,
            authority_id=authority_id,
            content_digest=_digest(payload),
            classification=classification,
            parent_digests=tuple(parent_digests),
        )

    @property
    def digest(self) -> str:
        return _digest(
            {
                "object_id": self.object_id,
                "authority_id": self.authority_id,
                "content_digest": self.content_digest,
                "classification": self.classification,
                "parent_digests": self.parent_digests,
            }
        )


@dataclass(frozen=True)
class InformationGrant:
    grant_id: str
    object_digest: str
    actor_id: str
    purpose: str
    allowed_tools: tuple[str, ...]
    issued_revision: int
    expires_at: datetime
    allow_derivation: bool = False
    allow_egress: bool = False
    allow_state_admission: bool = False


@dataclass(frozen=True)
class InformationSession:
    session_id: str
    grant_id: str
    opened_revision: int


@dataclass(frozen=True)
class InformationReceipt:
    event: str
    grant_id: str
    session_id: str
    object_digest: str
    result_digest: str | None
    state_revision: int
    receipt_digest: str


class InformationBoundary:
    """Local reference implementation of a fail-closed information boundary."""

    def __init__(self) -> None:
        self.state_revision = 1
        self._grants: dict[str, InformationGrant] = {}
        self._sessions: dict[str, InformationSession] = {}
        self._closed_sessions: set[str] = set()
        self._revoked_grants: set[str] = set()
        self._known_objects: dict[str, InformationObject] = {}

    def register(self, information: InformationObject) -> None:
        """Register only the object's governed envelope, never its raw content."""
        self._known_objects[information.digest] = information

    def issue_grant(
        self,
        information: InformationObject,
        *,
        actor_id: str,
        purpose: str,
        allowed_tools: Iterable[str],
        now: datetime,
        ttl_seconds: int = 300,
        allow_derivation: bool = False,
        allow_egress: bool = False,
        allow_state_admission: bool = False,
    ) -> InformationGrant:
        if now.tzinfo is None:
            raise InformationBoundaryError("timezone-aware time required")
        if ttl_seconds <= 0:
            raise InformationBoundaryError("ttl_seconds must be positive")
        tools = tuple(sorted(set(allowed_tools)))
        if not tools:
            raise InformationBoundaryError("at least one allowed tool is required")
        self.register(information)
        expires_at = now + timedelta(seconds=ttl_seconds)
        body = {
            "object": information.digest,
            "actor": actor_id,
            "purpose": purpose,
            "tools": tools,
            "revision": self.state_revision,
            "expires_at": expires_at.isoformat(),
            "allow_derivation": allow_derivation,
            "allow_egress": allow_egress,
            "allow_state_admission": allow_state_admission,
        }
        grant = InformationGrant(
            grant_id=_digest(body),
            object_digest=information.digest,
            actor_id=actor_id,
            purpose=purpose,
            allowed_tools=tools,
            issued_revision=self.state_revision,
            expires_at=expires_at,
            allow_derivation=allow_derivation,
            allow_egress=allow_egress,
            allow_state_admission=allow_state_admission,
        )
        self._grants[grant.grant_id] = grant
        return grant

    def revoke_grant(self, grant_id: str) -> None:
        if grant_id not in self._grants:
            raise InformationBoundaryError("unknown grant")
        self._revoked_grants.add(grant_id)
        self.state_revision += 1

    def open_session(
        self,
        grant: InformationGrant,
        *,
        actor_id: str,
        purpose: str,
        tool_id: str,
        now: datetime,
    ) -> InformationSession:
        self._validate_grant(grant, actor_id, purpose, tool_id, now)
        session = InformationSession(
            session_id=_digest(
                {
                    "grant": grant.grant_id,
                    "actor": actor_id,
                    "purpose": purpose,
                    "tool": tool_id,
                    "revision": self.state_revision,
                }
            ),
            grant_id=grant.grant_id,
            opened_revision=self.state_revision,
        )
        if session.session_id in self._closed_sessions:
            raise InformationBoundaryError("grant session already closed")
        self._sessions[session.session_id] = session
        return session

    def admit(self, session, grant, information, *, actor_id, purpose, tool_id, now):
        self._validate_session(session, grant, actor_id, purpose, tool_id, now)
        self._assert_known(information)
        if information.digest != grant.object_digest:
            raise InformationBoundaryError("grant is not bound to exact information object")
        return self._receipt("ADMIT", grant, session, information.digest)

    def derive(
        self,
        session,
        grant,
        source,
        *,
        derived_object_id,
        derived_payload,
        actor_id,
        purpose,
        tool_id,
        now,
    ):
        self._validate_session(session, grant, actor_id, purpose, tool_id, now)
        self._assert_known(source)
        self._assert_in_lineage(grant, source)
        if not grant.allow_derivation:
            raise InformationBoundaryError("derivation not allowed")
        root = self._known_objects[grant.object_digest]
        derived = InformationObject.from_payload(
            derived_object_id,
            root.authority_id,
            derived_payload,
            classification=root.classification,
            parent_digests=(source.digest,),
        )
        self.register(derived)
        return derived, self._receipt("DERIVE", grant, session, source.digest, derived.digest)

    def egress(self, session, grant, information, *, actor_id, purpose, tool_id, now):
        self._validate_session(session, grant, actor_id, purpose, tool_id, now)
        self._assert_known(information)
        self._assert_in_lineage(grant, information)
        if not grant.allow_egress:
            raise InformationBoundaryError("egress not allowed")
        return self._receipt("EGRESS", grant, session, information.digest)

    def admit_state(self, session, grant, information, *, actor_id, purpose, tool_id, now):
        self._validate_session(session, grant, actor_id, purpose, tool_id, now)
        self._assert_known(information)
        self._assert_in_lineage(grant, information)
        if not grant.allow_state_admission:
            raise InformationBoundaryError("state admission not allowed")
        return self._receipt("STATE_ADMIT", grant, session, information.digest)

    def close_session(self, session: InformationSession) -> InformationReceipt:
        known = self._sessions.get(session.session_id)
        if known != session:
            raise InformationBoundaryError("unknown session")
        if session.session_id in self._closed_sessions:
            raise InformationBoundaryError("session already closed")
        self._closed_sessions.add(session.session_id)
        grant = self._grants[session.grant_id]
        self._revoked_grants.add(grant.grant_id)
        self.state_revision += 1
        return self._receipt("CLOSE", grant, session, grant.object_digest)

    def _validate_grant(self, grant, actor_id, purpose, tool_id, now) -> None:
        if now.tzinfo is None:
            raise InformationBoundaryError("timezone-aware time required")
        canonical = self._grants.get(grant.grant_id)
        if canonical is None:
            raise InformationBoundaryError("unknown grant")
        if canonical != grant:
            raise InformationBoundaryError("grant does not match issued grant")
        if grant.grant_id in self._revoked_grants:
            raise InformationBoundaryError("grant revoked")
        if now >= grant.expires_at:
            raise InformationBoundaryError("grant expired")
        if grant.actor_id != actor_id:
            raise InformationBoundaryError("actor mismatch")
        if grant.purpose != purpose:
            raise InformationBoundaryError("purpose mismatch")
        if tool_id not in grant.allowed_tools:
            raise InformationBoundaryError("tool not allowed")

    def _validate_session(self, session, grant, actor_id, purpose, tool_id, now) -> None:
        self._validate_grant(grant, actor_id, purpose, tool_id, now)
        known = self._sessions.get(session.session_id)
        if known != session or session.grant_id != grant.grant_id:
            raise InformationBoundaryError("session is not bound to grant")
        if session.session_id in self._closed_sessions:
            raise InformationBoundaryError("session closed")

    def _assert_known(self, information: InformationObject) -> None:
        if self._known_objects.get(information.digest) != information:
            raise InformationBoundaryError("unregistered information object")

    def _assert_in_lineage(self, grant: InformationGrant, information: InformationObject) -> None:
        if information.digest == grant.object_digest:
            return
        seen: set[str] = set()
        stack = [information]
        while stack:
            current = stack.pop()
            if current.digest in seen:
                continue
            seen.add(current.digest)
            for parent_digest in current.parent_digests:
                if parent_digest == grant.object_digest:
                    return
                parent = self._known_objects.get(parent_digest)
                if parent is not None:
                    stack.append(parent)
        raise InformationBoundaryError("information is outside granted lineage")

    def _receipt(self, event, grant, session, object_digest, result_digest=None):
        body = {
            "event": event,
            "grant_id": grant.grant_id,
            "session_id": session.session_id,
            "object_digest": object_digest,
            "result_digest": result_digest,
            "state_revision": self.state_revision,
        }
        digest = _digest(body)
        return InformationReceipt(
            event=event,
            grant_id=grant.grant_id,
            session_id=session.session_id,
            object_digest=object_digest,
            result_digest=result_digest,
            state_revision=self.state_revision,
            receipt_digest=digest,
        )


__all__ = [
    "InformationBoundary",
    "InformationBoundaryError",
    "InformationGrant",
    "InformationObject",
    "InformationReceipt",
    "InformationSession",
]
