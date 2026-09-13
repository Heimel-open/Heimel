"""Anakin implementation beneath Speider's provider-neutral acquisition boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
import os
import socket
from typing import Any, Callable, Mapping, Protocol, cast
from urllib.parse import urlparse

import httpx

from .models import (
    CostEstimate,
    ProviderRunHandle,
    ProviderRunState,
    ProviderRunStatus,
    RawAcquisitionRecord,
)
from .provider import (
    AcquisitionProviderError,
    ProviderAcquisitionRequest,
)


class AnakinProviderError(AcquisitionProviderError):
    """Anakin state or evidence cannot be verified and must not reach BARO."""


class _AnakinClientLike(Protocol):
    def scrape(
        self,
        *,
        url: str,
        timeout_seconds: float,
        max_response_bytes: int,
    ) -> Any: ...

    def close(self) -> None: ...


GrantVerifier = Callable[[ProviderAcquisitionRequest, bool], bool]


@dataclass(frozen=True)
class AnakinProviderConfig:
    """Runtime-only configuration; token values are excluded from repr/log output."""

    endpoint: str
    auth_token: str = field(repr=False)
    upstream_version: str
    tls_verify: bool = True
    timeout_seconds: float = 30.0
    max_response_bytes: int = 10_485_760  # 10 MiB
    telemetry_expected: str = "off"
    hosted_fallback: bool = False
    ai_extraction: bool = False

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "AnakinProviderConfig":
        values = os.environ if env is None else env
        endpoint = values.get("ANAKIN_ENDPOINT", "").strip()
        if not endpoint:
            raise AnakinProviderError("ANAKIN_ENDPOINT is required")
        token = values.get("ANAKIN_AUTH_TOKEN", "").strip()
        if not token:
            raise AnakinProviderError("ANAKIN_AUTH_TOKEN is required")
        upstream_version = values.get("ANAKIN_UPSTREAM_VERSION", "").strip()
        if not upstream_version:
            raise AnakinProviderError("ANAKIN_UPSTREAM_VERSION is required")
        tls_verify_raw = values.get("ANAKIN_TLS_VERIFY", "true").strip().lower()
        if tls_verify_raw not in {"true", "false"}:
            raise AnakinProviderError("ANAKIN_TLS_VERIFY must be boolean")
        tls_verify = tls_verify_raw == "true"
        try:
            timeout_seconds = float(values.get("ANAKIN_TIMEOUT_SECONDS", "30.0"))
        except ValueError as exc:
            raise AnakinProviderError("ANAKIN_TIMEOUT_SECONDS must be numeric") from exc
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise AnakinProviderError("ANAKIN_TIMEOUT_SECONDS must be finite and positive")
        try:
            max_response_bytes = int(values.get("ANAKIN_MAX_RESPONSE_BYTES", "10485760"))
        except ValueError as exc:
            raise AnakinProviderError("ANAKIN_MAX_RESPONSE_BYTES must be integer") from exc
        if max_response_bytes <= 0:
            raise AnakinProviderError("ANAKIN_MAX_RESPONSE_BYTES must be positive")
        telemetry_expected = values.get("ANAKIN_TELEMETRY_EXPECTED", "off").strip().lower()
        if telemetry_expected not in {"on", "off"}:
            raise AnakinProviderError("ANAKIN_TELEMETRY_EXPECTED must be 'on' or 'off'")
        hosted_fallback = values.get("ANAKIN_HOSTED_FALLBACK", "false").lower() == "true"
        ai_extraction = values.get("ANAKIN_AI_EXTRACTION", "false").lower() == "true"

        return cls(
            endpoint=endpoint,
            auth_token=token,
            upstream_version=upstream_version,
            tls_verify=tls_verify,
            timeout_seconds=timeout_seconds,
            max_response_bytes=max_response_bytes,
            telemetry_expected=telemetry_expected,
            hosted_fallback=hosted_fallback,
            ai_extraction=ai_extraction,
        )

    def create_client(self) -> _AnakinClientLike:
        """Construct the HTTP client without making a network request."""

        class _Client:
            def __init__(self, config: AnakinProviderConfig):
                self._config = config
                self._client = httpx.Client(
                    base_url=config.endpoint,
                    headers={
                        "Authorization": f"Bearer {config.auth_token}",
                        "Content-Type": "application/json",
                    },
                    timeout=config.timeout_seconds,
                    verify=config.tls_verify,
                )

            def scrape(
                self,
                *,
                url: str,
                timeout_seconds: float,
                max_response_bytes: int,
            ) -> Any:
                response = self._client.post(
                    "/v1/scrape",
                    json={"url": url},
                    timeout=timeout_seconds,
                )
                response.raise_for_status()
                data = response.json()
                if isinstance(data, dict) and "content" in data:
                    content = data["content"]
                    if isinstance(content, str) and len(content.encode("utf-8")) > max_response_bytes:
                        raise AnakinProviderError("response body exceeds size limit")
                return data

            def close(self) -> None:
                self._client.close()

        return _Client(self)


def _iso(value: Any, label: str) -> str:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise AnakinProviderError(f"{label} cannot be verified") from exc
    else:
        raise AnakinProviderError(f"{label} cannot be verified")
    if parsed.tzinfo is None:
        raise AnakinProviderError(f"{label} has no timezone")
    return parsed.astimezone(timezone.utc).isoformat()


def _canonicalize_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise AnakinProviderError("only http and https schemes are permitted")
    if parsed.username or parsed.password:
        raise AnakinProviderError("userinfo in URL is not permitted")
    hostname = parsed.hostname or ""
    if not hostname:
        raise AnakinProviderError("URL must have a hostname")
    scheme = parsed.scheme.lower()
    netloc = hostname.lower()
    default_port = 80 if scheme == "http" else 443
    if parsed.port is not None and parsed.port != default_port:
        netloc = f"{netloc}:{parsed.port}"
    return parsed._replace(scheme=scheme, netloc=netloc).geturl()


def _resolve_ips(hostname: str) -> tuple[str, ...]:
    try:
        addrs = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise AnakinProviderError(f"DNS resolution failed for {hostname}") from exc
    ips: list[str] = []
    for addr in addrs:
        ip = str(addr[4][0])
        if ip not in ips:
            ips.append(ip)
    return tuple(ips)


def _is_private_ip(ip: str) -> bool:
    try:
        if ip.startswith("127.") or ip == "::1":
            return True
        if ip.startswith("10.") or ip.startswith("192.168."):
            return True
        if ip.startswith("172.") and 16 <= int(ip.split(".")[1]) <= 31:
            return True
        if ip.startswith("169.254.") or ip.startswith("fe80:"):
            return True
        if ip.startswith("224.") or ip.startswith("ff") or ip == "::":
            return True
        if ip.startswith("0.") or ip == "0.0.0.0":
            return True
        if ip.startswith("100.64.") and 0 <= int(ip.split(".")[2]) <= 31:
            return True
    except (ValueError, IndexError):
        return True
    return False


def _is_metadata_target(hostname: str) -> bool:
    metadata_hosts = {
        "metadata.google.internal",
        "metadata.azure.com",
        "169.254.169.254",
        "metadata.ec2.internal",
        "instance-data.ec2.internal",
        "metadata.packet.net",
        "metadata.digitalocean.com",
    }
    return hostname.lower() in metadata_hosts


def _check_ssrf(hostname: str, ips: tuple[str, ...]) -> None:
    if not ips:
        raise AnakinProviderError("DNS resolution returned no addresses")
    if _is_metadata_target(hostname) or any(_is_metadata_target(ip) for ip in ips):
        raise AnakinProviderError("resolved address is a cloud metadata target")
    public_ips = [ip for ip in ips if not _is_private_ip(ip)]
    private_ips = [ip for ip in ips if _is_private_ip(ip)]
    if public_ips and private_ips:
        raise AnakinProviderError("mixed public and private DNS answers detected")
    if private_ips:
        raise AnakinProviderError("resolved address is in private or reserved range")


class AnakinAcquisitionProvider:
    """Execute one registry-authorized, version-pinned Anakin scrape without store discovery."""

    provider_name = "anakin"

    def __init__(
        self,
        config: AnakinProviderConfig,
        *,
        grant_verifier: GrantVerifier,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._config = config
        self._grant_verifier = grant_verifier
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._client = config.create_client()

    def validate_request(self, request: ProviderAcquisitionRequest) -> None:
        if not self._grant_verifier(request, False):
            raise AnakinProviderError("registry execution grant is invalid")
        if not request.requested_source or not request.source_platform:
            raise AnakinProviderError("source scope cannot be verified")
        if (
            isinstance(request.max_cost_usd, bool)
            or not isinstance(request.max_cost_usd, (int, float))
            or not math.isfinite(float(request.max_cost_usd))
            or request.max_cost_usd <= 0
        ):
            raise AnakinProviderError("cost ceiling cannot be verified")
        max_timeout = request.resource_limits.get("max_timeout_seconds")
        if not isinstance(max_timeout, int) or request.timeout_seconds <= 0:
            raise AnakinProviderError("timeout limit cannot be verified")
        if request.timeout_seconds > max_timeout:
            raise AnakinProviderError("timeout exceeds registry limit")

    def estimate_cost(self, request: ProviderAcquisitionRequest) -> CostEstimate:
        self.validate_request(request)
        return CostEstimate(
            amount_usd=0.0,
            is_hard_ceiling=True,
            basis="local-infrastructure-zero-cost-hard-ceiling",
            metadata={"currency": "USD", "provider": self.provider_name},
        )

    def start_run(self, request: ProviderAcquisitionRequest) -> ProviderRunHandle:
        self.validate_request(request)
        if not self._grant_verifier(request, True):
            raise AnakinProviderError("registry execution grant is invalid or already used")
        requested_url = request.requested_source
        canonical_url = _canonicalize_url(requested_url)
        hostname = urlparse(canonical_url).hostname or ""
        ips = _resolve_ips(hostname)
        _check_ssrf(hostname, ips)
        started_at = self._clock().isoformat()
        handle = ProviderRunHandle(
            provider_name=self.provider_name,
            run_id=f"anakin-{started_at.replace(':', '').replace('-', '')}-{abs(hash(canonical_url)) % 1000000:06d}",
            actor_id=request.actor_id,
            actor_version=request.actor_version,
            started_at=started_at,
            metadata={
                "requested_source": request.requested_source,
                "source_platform": request.source_platform,
                "correlation_id": request.correlation_id,
                "canonical_url": canonical_url,
                "resolved_ips": ips,
            },
        )
        return handle

    def get_run_status(self, handle: ProviderRunHandle) -> ProviderRunStatus:
        self._validate_handle(handle)
        return ProviderRunStatus(
            handle=handle,
            state=ProviderRunState.SUCCEEDED,
            checked_at=self._clock().isoformat(),
            dataset_ref=handle.run_id,
            cost_metadata={"total_usd": 0.0, "cost_final": True},
            execution_metadata={"status": "completed"},
        )

    def fetch_dataset(self, handle: ProviderRunHandle) -> RawAcquisitionRecord:
        self._validate_handle(handle)
        canonical_url = handle.metadata.get("canonical_url")
        if not canonical_url:
            raise AnakinProviderError("canonical URL missing from handle")
        resolved_ips = handle.metadata.get("resolved_ips", ())
        if resolved_ips:
            _check_ssrf(urlparse(canonical_url).hostname or "", tuple(resolved_ips))
        response = self._client.scrape(
            url=canonical_url,
            timeout_seconds=self._config.timeout_seconds,
            max_response_bytes=self._config.max_response_bytes,
        )
        if not isinstance(response, dict):
            raise AnakinProviderError("Anakin response cannot be verified")
        if response.get("upstream_version") != self._config.upstream_version:
            raise AnakinProviderError("Anakin upstream version mismatch")
        if self._config.telemetry_expected == "off":
            telemetry = response.get("telemetry", {})
            if telemetry.get("enabled") is True:
                raise AnakinProviderError("Anakin telemetry enabled in off deployment")
        status = response.get("status")
        if not isinstance(status, int) or status < 200 or status >= 300:
            raise AnakinProviderError(f"Anakin returned non-success status: {status}")
        final_url = response.get("final_url")
        if not final_url or not isinstance(final_url, str):
            raise AnakinProviderError("final URL missing from Anakin response")
        if _canonicalize_url(final_url) != canonical_url:
            raise AnakinProviderError("final URL does not match requested canonical URL")
        handler = response.get("handler")
        if not handler or not isinstance(handler, str):
            raise AnakinProviderError("handler metadata missing from Anakin response")
        duration_ms = response.get("duration_ms")
        if not isinstance(duration_ms, (int, float)) or duration_ms < 0:
            raise AnakinProviderError("duration metadata missing or invalid")
        content = response.get("content")
        if not content or not isinstance(content, str):
            raise AnakinProviderError("content missing from Anakin response")
        raw_html = content
        cleaned_html = response.get("cleaned_html")
        markdown = response.get("markdown")
        generated_json = response.get("generated_json")
        retrieved_at = self._clock().isoformat()
        executed_at = handle.started_at
        return RawAcquisitionRecord(
            provider_name=self.provider_name,
            actor_id=handle.actor_id,
            actor_version=handle.actor_version,
            run_id=handle.run_id,
            dataset_ref=handle.run_id,
            source_identifier=handle.metadata["requested_source"],
            source_platform=handle.metadata["source_platform"],
            retrieved_at=retrieved_at,
            executed_at=executed_at,
            payload={
                "raw_html": raw_html,
                "cleaned_html": cleaned_html,
                "markdown": markdown,
                "generated_json": generated_json,
                "final_url": final_url,
                "handler": handler,
                "duration_ms": duration_ms,
                "status": status,
                "upstream_version": self._config.upstream_version,
            },
            cost_metadata={"total_usd": 0.0},
            execution_metadata={
                "status": status,
                "final_url": final_url,
                "handler": handler,
                "duration_ms": duration_ms,
                "upstream_version": self._config.upstream_version,
                "resolved_ips": resolved_ips,
                "correlation_id": handle.metadata.get("correlation_id"),
            },
        )

    def cancel_run(self, handle: ProviderRunHandle) -> None:
        self._validate_handle(handle)

    def _validate_handle(self, handle: ProviderRunHandle) -> None:
        if handle.provider_name != self.provider_name or not handle.run_id:
            raise AnakinProviderError("provider run handle is invalid")

    def close(self) -> None:
        if hasattr(self._client, "close"):
            self._client.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass