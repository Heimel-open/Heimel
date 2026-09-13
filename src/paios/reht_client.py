"""
REHT client — thin adapter that calls the REHT admissibility authority.

Supports TWO modes:
  (a) In-process: imports services.reht.service.evaluate_canonical directly
      IF the valo-platform package is importable (same process).
  (b) HTTP: POSTs to VALO_REHT_URL/evaluate/canonical env-var if remote.

Never hardcodes a URL. REHT is the SOLE admissibility authority — PAIOS
calls it, never re-decides.

Canonical rules:
  - REHT sole admissibility authority — PAIOS proposes, REHT decides.
  - Canonical REHT types reused when importable; compatible PAIOS-side
    types defined as fallback.
  - AdmissibilityState is NEVER redefined — only referenced.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


# ------------------------------------------------------------------
# Canonical REHT type reuse — import if available, reference only
# ------------------------------------------------------------------

try:
    from services.reht.service import AdmissibilityState  # type: ignore[import-untyped]
    _HAS_IN_PROCESS_REHT = True
except ImportError:
    _HAS_IN_PROCESS_REHT = False

    # Reference-only — NOT a redefinition of AdmissibilityState.
    # These string constants mirror the canonical enum values so the
    # PAIOS-side dataclass can represent verdicts from any REHT mode.
    class AdmissibilityState:  # type: ignore[no-redef]
        ADMISSIBLE = "ADMISSIBLE"
        INADMISSIBLE = "INADMISSIBLE"
        INDETERMINATE = "INDETERMINATE"
        REQUIRES_STEP_UP = "REQUIRES_STEP_UP"
        NO_LONGER_ADMISSIBLE = "NO_LONGER_ADMISSIBLE"


# ------------------------------------------------------------------
# PAIOS-side admissibility verdict — compatible with canonical shape
# ------------------------------------------------------------------


@dataclass(frozen=True)
class AdmissibilityVerdict:
    """PAIOS-side representation of a REHT admissibility verdict.

    Compatible with the canonical REHT AdmissibilityResult shape.
    Carries the state as a string (AdmissibilityState value), plus
    the scalar admissible flag, score, reasons, and optional clearance.
    """

    state: str
    admissible: bool
    score: float
    reasons: list[str]
    governance_clearance: dict[str, Any] | None = None
    policy_applied: str | None = None


# ------------------------------------------------------------------
# REHT client
# ------------------------------------------------------------------


class RehtClientError(RuntimeError):
    """Raised when the REHT client cannot reach or process a response."""


class RehtClient:
    """Thin client that calls REHT for admissibility evaluation.

    Mode selection (priority order):
      1. In-process — import services.reht.service if valo-platform
         is available in the same Python environment.
      2. HTTP — POST to ``VALO_REHT_URL``/evaluate/canonical.

    Raises ``RehtClientError`` if neither mode is available.
    Never hardcodes a URL.
    """

    def __init__(self) -> None:
        self._url: str = os.environ.get("VALO_REHT_URL", "").rstrip("/")

    @property
    def mode(self) -> str:
        """Human-readable mode description (in-process | http | none)."""
        if _HAS_IN_PROCESS_REHT:
            return "in-process"
        if self._url:
            return "http"
        return "none"

    def evaluate(self, envelope: Any, **kwargs: Any) -> AdmissibilityVerdict:
        """Evaluate an action envelope through REHT.

        Args:
            envelope: An ActionEnvelope (or any object with ``action_id``,
                ``action_type``, ``actor``, ``to_dict``, ``evidence_package``,
                ``risk_context`` attributes).

        Returns:
            An ``AdmissibilityVerdict``.

        Raises:
            RehtClientError: if neither in-process nor HTTP mode is available,
                or if the HTTP request fails.
        """
        if _HAS_IN_PROCESS_REHT:
            return self._evaluate_in_process(envelope)
        if self._url:
            return self._evaluate_http(envelope)
        raise RehtClientError(
            "No REHT endpoint configured: valo-platform not importable "
            "and VALO_REHT_URL env var not set"
        )

    # -- In-process mode ------------------------------------------------

    def _evaluate_in_process(self, envelope: Any) -> AdmissibilityVerdict:
        from services.reht.service import RehtService

        service = RehtService()
        result = service.evaluate_canonical(
            tenant_id=envelope.actor.get("tenant_id", "default"),
            task_id=envelope.action_id,
            action=envelope.action_type,
            risk_level=(
                envelope.risk_context.get("level", "medium")
                if envelope.risk_context
                else "medium"
            ),
            context=envelope.to_dict(),
            evidence=getattr(envelope, "evidence_package", {}),
        )
        return AdmissibilityVerdict(
            state=result.state.value,
            admissible=result.admissible,
            score=result.score,
            reasons=list(result.reasons),
            governance_clearance=(
                result.governance_clearance.__dict__
                if result.governance_clearance
                else None
            ),
            policy_applied=result.policy_applied,
        )

    # -- HTTP mode ------------------------------------------------------

    def _evaluate_http(self, envelope: Any) -> AdmissibilityVerdict:
        url = f"{self._url}/evaluate/canonical"
        payload = json.dumps(
            {
                "tenant_id": envelope.actor.get("tenant_id", "default"),
                "task_id": envelope.action_id,
                "action": envelope.action_type,
                "risk_level": (
                    envelope.risk_context.get("level", "medium")
                    if envelope.risk_context
                    else "medium"
                ),
                "context": envelope.to_dict(),
                "evidence": getattr(envelope, "evidence_package", {}),
            }
        ).encode("utf-8")

        req = Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(req) as resp:
                data: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
        except URLError as e:
            raise RehtClientError(f"REHT HTTP request failed: {e}") from e

        return AdmissibilityVerdict(
            state=data.get("state", AdmissibilityState.INDETERMINATE),
            admissible=data.get("admissible", False),
            score=data.get("score", 0.0),
            reasons=data.get("reasons", []),
            governance_clearance=data.get("governance_clearance"),
            policy_applied=data.get("policy_applied"),
        )
