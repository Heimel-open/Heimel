"""Dedicated HTTP service for VAIG second-operator Coherence replay.

Deploy separately from the primary evaluation service, with a dedicated operator
identity and credential, e.g.:

    VAIG_COHERENCE_REPLAY_OPERATOR_REF=operator:replay-2 \
    VAIG_COHERENCE_REPLAY_TOKEN=... \
    uvicorn vaig.coherence_replay_api:app --host 0.0.0.0 --port 8003

This service is evaluation evidence only. It cannot issue REHT clearance.
"""
from __future__ import annotations

import hmac
import os
from typing import Any, Dict

from fastapi import Body, FastAPI, Header, HTTPException, status

from .coherence_replay import CoherenceReplayError, replay_frozen_packet


app = FastAPI(
    title="VAIG Coherence Second-Operator Replay API",
    description=(
        "Independent deterministic replay of a frozen pre-replay Coherence packet. "
        "Outputs are evidence only and require downstream REHT clearance."
    ),
    version="1.0.0",
)


def _configuration() -> tuple[str, str]:
    operator_ref = os.getenv("VAIG_COHERENCE_REPLAY_OPERATOR_REF", "").strip()
    token = os.getenv("VAIG_COHERENCE_REPLAY_TOKEN", "").strip()
    if not operator_ref or not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="second-operator replay service is not configured",
        )
    return operator_ref, token


def _require_token(authorization: str | None, token: str) -> None:
    expected = f"Bearer {token}"
    if authorization is None or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")


@app.post(
    "/api/v1/coherence/replay",
    status_code=status.HTTP_200_OK,
    tags=["Coherence Replay"],
)
async def replay_coherence(
    payload: Dict[str, Any] = Body(...),
    authorization: str | None = Header(default=None),
):
    operator_ref, token = _configuration()
    _require_token(authorization, token)
    try:
        return replay_frozen_packet(payload, operator_ref=operator_ref)
    except CoherenceReplayError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/healthz", tags=["System"])
async def healthz():
    operator_ref = os.getenv("VAIG_COHERENCE_REPLAY_OPERATOR_REF", "").strip()
    token_configured = bool(os.getenv("VAIG_COHERENCE_REPLAY_TOKEN", "").strip())
    return {
        "status": "ok" if operator_ref and token_configured else "misconfigured",
        "service": "vaig-coherence-second-operator-replay",
        "operator_ref": operator_ref or None,
        "operator_kind": "INDEPENDENT",
        "blind_to_prior_replay_outcome": True,
        "execution_authority": False,
        "requires_reht_clearance": True,
    }


__all__ = ["app", "replay_coherence"]
