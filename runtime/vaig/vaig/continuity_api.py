"""Dedicated network service for VAIG Operational Continuity assessment.

This app is intentionally separate from the legacy demonstration authorization
API. Its only consequence-bearing output is a materiality assessment artifact.
It never issues clearance, AARM decisions, CommitTokens or execution permits.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import Body, FastAPI, HTTPException, status

from .continuity_assessment import (
    ContinuityAssessmentError,
    SCHEMA_VERSION,
    SERVICE_ID,
)
from .continuity_wire import WIRE_SCHEMA_VERSION, assess_continuity_wire


app = FastAPI(
    title="VAIG Operational Continuity Assessment",
    description=(
        "Read-only VAIG materiality assessment for digest-bound Operational "
        "Continuity revalidation requests."
    ),
    version="1.0.0",
    docs_url="/api/v1/docs",
    redoc_url=None,
    openapi_url="/api/v1/openapi.json",
)


@app.post(
    "/api/v1/continuity/assess",
    status_code=status.HTTP_200_OK,
    tags=["Operational Continuity"],
)
async def assess_continuity(
    payload: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    """Return a VAIG assessment; never return authorization or execution state."""

    try:
        return assess_continuity_wire(payload)
    except ContinuityAssessmentError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@app.get(
    "/api/v1/health",
    status_code=status.HTTP_200_OK,
    tags=["System"],
)
async def health() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service_id": SERVICE_ID,
        "assessment_schema_version": SCHEMA_VERSION,
        "wire_schema_version": WIRE_SCHEMA_VERSION,
        "evaluation_only": True,
        "grants_clearance": False,
        "grants_execution": False,
    }


__all__ = ["app", "assess_continuity", "health"]
