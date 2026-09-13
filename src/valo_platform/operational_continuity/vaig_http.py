"""Strict HTTP client for the VAIG Operational Continuity assessment service.

The client sends one complete digest-bound ContinuityRevalidationRequest and the
exact commit checkpoint time. It accepts only a ContinuityImpactAssessment and
fails closed on transport, schema, identity, digest, binding or time mismatch.

It does not call VAIG's legacy authorization endpoint and cannot receive or map
clearance, AARM outcomes, CommitTokens or execution permits.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol
from urllib.parse import urlparse

from src.valo_platform.decision_governance.continuity import (
    ContinuityImpactAssessment,
)

from .revalidation import (
    ContinuityRevalidationRequest,
    validate_vaig_assessment,
)


WIRE_SCHEMA_VERSION = "operational-continuity-vaig-request/1.0"
ASSESSMENT_SCHEMA_VERSION = "operational-continuity-vaig-assessment/1.0"
SERVICE_ID = "vaig-continuity-assessment"
ASSESSOR_REF = "vaig:continuity-assessment:1.0"
ENDPOINT_PATH = "/api/v1/continuity/assess"

_DISALLOWED_RESPONSE_KEYS = {
    "decision",
    "clearance",
    "aarm_outcome",
    "racs_outcome",
    "commit_token",
    "execution_permit",
    "authorization",
}


class VaigContinuityClientError(RuntimeError):
    """Raised when remote VAIG assessment cannot be trusted or completed."""


class HttpResponse(Protocol):
    status_code: int
    headers: Mapping[str, str]
    content: bytes

    def json(self) -> Any:
        ...


class HttpSession(Protocol):
    def post(
        self,
        url: str,
        *,
        json: Mapping[str, Any],
        headers: Mapping[str, str],
        timeout: float,
    ) -> HttpResponse:
        ...


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise VaigContinuityClientError(
            "VAIG_CONTINUITY_ASSESSED_AT_MUST_BE_AWARE"
        )
    return value.astimezone(timezone.utc)


def _wire_timestamp(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _is_local_host(hostname: str | None) -> bool:
    return hostname in {"localhost", "127.0.0.1", "::1"}


def _validate_base_url(
    base_url: str,
    *,
    allow_insecure_localhost: bool,
) -> str:
    parsed = urlparse(base_url)
    if parsed.username or parsed.password:
        raise VaigContinuityClientError(
            "VAIG_CONTINUITY_URL_USERINFO_FORBIDDEN"
        )
    if parsed.query or parsed.fragment:
        raise VaigContinuityClientError(
            "VAIG_CONTINUITY_URL_QUERY_OR_FRAGMENT_FORBIDDEN"
        )
    if not parsed.hostname:
        raise VaigContinuityClientError("VAIG_CONTINUITY_URL_HOST_REQUIRED")
    if parsed.scheme == "https":
        pass
    elif (
        parsed.scheme == "http"
        and allow_insecure_localhost
        and _is_local_host(parsed.hostname)
    ):
        pass
    else:
        raise VaigContinuityClientError(
            "VAIG_CONTINUITY_HTTPS_REQUIRED"
        )
    return base_url.rstrip("/")


def _default_session() -> HttpSession:
    try:
        import requests
    except Exception as exc:  # pragma: no cover - dependency is packaged
        raise VaigContinuityClientError(
            "VAIG_CONTINUITY_HTTP_CLIENT_UNAVAILABLE"
        ) from exc
    return requests.Session()


def _response_json(response: HttpResponse, *, max_response_bytes: int) -> Any:
    content = getattr(response, "content", b"")
    if isinstance(content, bytes) and len(content) > max_response_bytes:
        raise VaigContinuityClientError(
            "VAIG_CONTINUITY_RESPONSE_TOO_LARGE"
        )
    content_type = ""
    headers = getattr(response, "headers", {})
    if isinstance(headers, Mapping):
        content_type = str(headers.get("content-type", headers.get("Content-Type", "")))
    if content_type and "application/json" not in content_type.lower():
        raise VaigContinuityClientError(
            "VAIG_CONTINUITY_RESPONSE_NOT_JSON"
        )
    try:
        return response.json()
    except Exception as exc:
        raise VaigContinuityClientError(
            "VAIG_CONTINUITY_RESPONSE_JSON_INVALID"
        ) from exc


def _contains_disallowed_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key).lower() in _DISALLOWED_RESPONSE_KEYS:
                return True
            if _contains_disallowed_key(nested):
                return True
    elif isinstance(value, list):
        return any(_contains_disallowed_key(item) for item in value)
    return False


@dataclass(frozen=True)
class VaigHttpContinuityAssessmentPort:
    """Production VAIG assessment port for OperationalContinuityRuntime."""

    base_url: str
    bearer_token: str | None = None
    timeout_seconds: float = 5.0
    allow_insecure_localhost: bool = False
    max_response_bytes: int = 1_048_576
    session: HttpSession | None = None

    def __post_init__(self) -> None:
        normalized = _validate_base_url(
            self.base_url,
            allow_insecure_localhost=self.allow_insecure_localhost,
        )
        object.__setattr__(self, "base_url", normalized)
        if self.timeout_seconds <= 0 or self.timeout_seconds > 30:
            raise VaigContinuityClientError(
                "VAIG_CONTINUITY_TIMEOUT_INVALID"
            )
        if self.max_response_bytes <= 0 or self.max_response_bytes > 10_485_760:
            raise VaigContinuityClientError(
                "VAIG_CONTINUITY_RESPONSE_LIMIT_INVALID"
            )
        if self.bearer_token is not None and not self.bearer_token.strip():
            raise VaigContinuityClientError(
                "VAIG_CONTINUITY_BEARER_TOKEN_INVALID"
            )

    @property
    def endpoint_url(self) -> str:
        return self.base_url + ENDPOINT_PATH

    def assess(
        self,
        request: ContinuityRevalidationRequest,
        *,
        assessed_at: datetime,
    ) -> ContinuityImpactAssessment:
        assessed_at = _as_utc(assessed_at)
        payload = {
            "schema_version": WIRE_SCHEMA_VERSION,
            "assessed_at": _wire_timestamp(assessed_at),
            "request": request.model_dump(mode="json"),
        }
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Continuity-Request-Digest": request.request_digest,
            "X-Continuity-Action-Case": request.basis.action_case_id,
        }
        if self.bearer_token is not None:
            headers["Authorization"] = f"Bearer {self.bearer_token}"

        session = self.session or _default_session()
        try:
            response = session.post(
                self.endpoint_url,
                json=payload,
                headers=headers,
                timeout=float(self.timeout_seconds),
            )
        except Exception as exc:
            raise VaigContinuityClientError(
                "VAIG_CONTINUITY_TRANSPORT_FAILED"
            ) from exc

        if response.status_code != 200:
            raise VaigContinuityClientError(
                f"VAIG_CONTINUITY_HTTP_STATUS:{response.status_code}"
            )
        raw = _response_json(
            response,
            max_response_bytes=self.max_response_bytes,
        )
        if not isinstance(raw, Mapping):
            raise VaigContinuityClientError(
                "VAIG_CONTINUITY_RESPONSE_OBJECT_REQUIRED"
            )
        expected_keys = {
            "schema_version",
            "service_id",
            "request_ref",
            "request_digest",
            "assessment",
        }
        if set(raw) != expected_keys:
            raise VaigContinuityClientError(
                "VAIG_CONTINUITY_RESPONSE_SCHEMA_INVALID"
            )
        if _contains_disallowed_key(raw):
            raise VaigContinuityClientError(
                "VAIG_CONTINUITY_AUTHORIZATION_OUTPUT_FORBIDDEN"
            )
        if raw.get("schema_version") != ASSESSMENT_SCHEMA_VERSION:
            raise VaigContinuityClientError(
                "VAIG_CONTINUITY_ASSESSMENT_SCHEMA_UNSUPPORTED"
            )
        if raw.get("service_id") != SERVICE_ID:
            raise VaigContinuityClientError(
                "VAIG_CONTINUITY_SERVICE_ID_MISMATCH"
            )
        if raw.get("request_ref") != request.evidence_ref:
            raise VaigContinuityClientError(
                "VAIG_CONTINUITY_REQUEST_REF_MISMATCH"
            )
        if raw.get("request_digest") != request.request_digest:
            raise VaigContinuityClientError(
                "VAIG_CONTINUITY_REQUEST_DIGEST_MISMATCH"
            )
        assessment_raw = raw.get("assessment")
        if not isinstance(assessment_raw, Mapping):
            raise VaigContinuityClientError(
                "VAIG_CONTINUITY_ASSESSMENT_OBJECT_REQUIRED"
            )
        try:
            assessment = ContinuityImpactAssessment(**dict(assessment_raw))
        except Exception as exc:
            raise VaigContinuityClientError(
                "VAIG_CONTINUITY_ASSESSMENT_CONTRACT_INVALID"
            ) from exc
        if assessment.assessed_at != assessed_at:
            raise VaigContinuityClientError(
                "VAIG_CONTINUITY_ASSESSMENT_TIME_MISMATCH"
            )
        if ASSESSOR_REF not in assessment.assessor_refs:
            raise VaigContinuityClientError(
                "VAIG_CONTINUITY_ASSESSOR_REF_MISSING"
            )
        try:
            validate_vaig_assessment(request, assessment)
        except Exception as exc:
            raise VaigContinuityClientError(
                "VAIG_CONTINUITY_ASSESSMENT_BINDING_INVALID"
            ) from exc
        return assessment


__all__ = [
    "ASSESSMENT_SCHEMA_VERSION",
    "ASSESSOR_REF",
    "ENDPOINT_PATH",
    "SERVICE_ID",
    "VaigContinuityClientError",
    "VaigHttpContinuityAssessmentPort",
    "WIRE_SCHEMA_VERSION",
]
