"""Dedicated HTTP surface for the canonical VAIG coherence evaluator.

Run with e.g. ``uvicorn vaig.coherence_api:app --host 0.0.0.0 --port 8002``.
This service returns evaluation evidence only and never issues REHT clearance.
Set ``VAIG_COHERENCE_TOKEN`` to require a bearer token on evaluation requests.
"""

import hmac
import os
from typing import Any, Dict

from fastapi import Body, FastAPI, Header, HTTPException, status

from .coherence_service import CoherenceTransportError, evaluate_and_bind


app = FastAPI(
    title="VAIG Coherence Evaluation API",
    description=(
        "Deterministic Coherence Live-Fire evaluation transport. "
        "Outputs are digest-bound VAIG evidence and require downstream REHT clearance."
    ),
    version="1.0.0",
)


def _require_service_token(authorization: str | None) -> None:
    configured = os.getenv("VAIG_COHERENCE_TOKEN", "")
    if not configured:
        return
    expected = f"Bearer {configured}"
    if authorization is None or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")


@app.post(
    "/api/v1/coherence/evaluate",
    status_code=status.HTTP_200_OK,
    tags=["Coherence Evaluation"],
)
async def evaluate_coherence(
    payload: Dict[str, Any] = Body(...),
    authorization: str | None = Header(default=None),
):
    """Evaluate one canonical CoherenceEvaluationInputV1 JSON object."""
    _require_service_token(authorization)
    try:
        return evaluate_and_bind(payload)
    except CoherenceTransportError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/healthz", tags=["System"])
async def healthz():
    return {
        "status": "ok",
        "service": "vaig-coherence-evaluation",
        "execution_authority": False,
        "requires_reht_clearance": True,
    }


__all__ = ["app", "evaluate_coherence"]
