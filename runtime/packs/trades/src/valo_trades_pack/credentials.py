from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class CredentialRequirement:
    credential_type: str
    minimum_status: str = "VERIFIED"


@dataclass
class WorkerCredential:
    worker_id: str
    credential_type: str
    valid_from: datetime
    valid_until: datetime
    status: str = "VERIFIED"  # VERIFIED | EXPIRED | REVOKED


def _as_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def credential_valid(credential: dict[str, Any] | WorkerCredential, moment: datetime) -> bool:
    """A credential is valid when it is VERIFIED and valid at `moment`."""
    if isinstance(credential, WorkerCredential):
        status = credential.status
        valid_from = credential.valid_from
        valid_until = credential.valid_until
    else:
        status = credential.get("status", "VERIFIED")
        valid_from = _as_dt(credential.get("valid_from", "1970-01-01T00:00:00+00:00"))
        valid_until = _as_dt(credential.get("valid_until", "9999-01-01T00:00:00+00:00"))
    return status == "VERIFIED" and valid_from <= moment < valid_until


def verify_trade_credential(worker: dict[str, Any], requirement: CredentialRequirement, moment: datetime) -> bool:
    """A worker is qualified only if EVERY required credential is verified and
    valid at `moment`. Missing or expired credentials exclude the worker — never
    compensated by agent judgment later."""
    for credential in worker.get("credentials", []):
        if credential.get("credential_type") == requirement.credential_type:
            return credential_valid(credential, moment)
    return False
