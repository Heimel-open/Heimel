"""Apify implementation beneath Speider's provider-neutral acquisition boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import math
import os
from typing import Any, Callable, Mapping, Protocol, cast

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


class ApifyProviderError(AcquisitionProviderError):
    """Apify state or evidence cannot be verified and must not reach BARO."""


class _ActorClient(Protocol):
    def start(self, **kwargs: Any) -> Any: ...


class _RunClient(Protocol):
    def get(self, **kwargs: Any) -> Any | None: ...

    def abort(self, **kwargs: Any) -> Any: ...


class _DatasetClient(Protocol):
    def list_items(self, **kwargs: Any) -> Any: ...


class ApifyClientLike(Protocol):
    def actor(self, actor_id: str) -> _ActorClient: ...

    def run(self, run_id: str) -> _RunClient: ...

    def dataset(self, dataset_id: str) -> _DatasetClient: ...


GrantVerifier = Callable[[ProviderAcquisitionRequest, bool], bool]


@dataclass(frozen=True)
class ApifyProviderConfig:
    """Runtime-only configuration; token values are excluded from repr/log output."""

    api_token: str = field(repr=False)
    api_url: str = "https://api.apify.com"
    api_public_url: str = "https://api.apify.com"
    poll_interval_seconds: float = 1.0

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "ApifyProviderConfig":
        values = os.environ if env is None else env
        token = values.get("APIFY_API_TOKEN", "").strip()
        if not token:
            raise ApifyProviderError("APIFY_API_TOKEN is required")
        try:
            poll_interval = float(
                values.get("SPEIDER_APIFY_POLL_INTERVAL_SECONDS", "1.0")
            )
        except ValueError as exc:
            raise ApifyProviderError(
                "SPEIDER_APIFY_POLL_INTERVAL_SECONDS must be numeric"
            ) from exc
        if not math.isfinite(poll_interval) or poll_interval <= 0:
            raise ApifyProviderError(
                "SPEIDER_APIFY_POLL_INTERVAL_SECONDS must be finite and positive"
            )
        return cls(
            api_token=token,
            api_url=values.get("APIFY_API_URL", "https://api.apify.com"),
            api_public_url=values.get("APIFY_API_PUBLIC_URL", "https://api.apify.com"),
            poll_interval_seconds=poll_interval,
        )

    def create_client(self) -> ApifyClientLike:
        """Construct the SDK client without making a network request."""
        from apify_client import ApifyClient

        return cast(
            ApifyClientLike,
            ApifyClient(
                token=self.api_token,
                api_url=self.api_url,
                api_public_url=self.api_public_url,
            ),
        )


def _iso(value: Any, label: str) -> str:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ApifyProviderError(f"{label} cannot be verified") from exc
    else:
        raise ApifyProviderError(f"{label} cannot be verified")
    if parsed.tzinfo is None:
        raise ApifyProviderError(f"{label} has no timezone")
    return parsed.astimezone(timezone.utc).isoformat()


def _finite_cost(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ApifyProviderError("Apify cost cannot be verified")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ApifyProviderError("Apify cost cannot be verified")
    return result


def _normalize_run_response(value: Any, label: str) -> dict[str, Any]:
    """Normalize Mapping or apify-client Run fields without SDK serialization."""
    aliases = (
        ("id", "id"),
        ("actId", "act_id"),
        ("status", "status"),
        ("buildId", "build_id"),
        ("buildNumber", "build_number"),
        ("defaultDatasetId", "default_dataset_id"),
        ("startedAt", "started_at"),
        ("finishedAt", "finished_at"),
        ("usageTotalUsd", "usage_total_usd"),
        ("usageUsd", "usage_usd"),
        ("stats", "stats"),
        ("chargedEventCounts", "charged_event_counts"),
    )
    if isinstance(value, Mapping):
        result = {alias: value.get(alias) for alias, _ in aliases}
    elif value is not None and any(hasattr(value, attr) for _, attr in aliases):
        result = {alias: getattr(value, attr, None) for alias, attr in aliases}
    else:
        raise ApifyProviderError(f"{label} cannot be verified")

    status = result["status"]
    if not isinstance(status, str) and hasattr(status, "value"):
        result["status"] = getattr(status, "value")

    stats = result["stats"]
    if isinstance(stats, Mapping):
        compute_units = stats.get("computeUnits", stats.get("compute_units"))
    else:
        compute_units = getattr(stats, "compute_units", None)
    result["stats"] = (
        {"computeUnits": compute_units} if compute_units is not None else {}
    )

    usage_usd = result["usageUsd"]
    result["usageUsd"] = dict(usage_usd) if isinstance(usage_usd, Mapping) else {}
    charged_counts = result["chargedEventCounts"]
    result["chargedEventCounts"] = (
        dict(charged_counts) if isinstance(charged_counts, Mapping) else {}
    )
    return result


class ApifyAcquisitionProvider:
    """Execute one registry-authorized, version-pinned Actor without Store discovery."""

    provider_name = "apify"

    def __init__(
        self,
        client: ApifyClientLike,
        *,
        grant_verifier: GrantVerifier,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._client = client
        self._grant_verifier = grant_verifier
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def validate_request(self, request: ProviderAcquisitionRequest) -> None:
        if not self._grant_verifier(request, False):
            raise ApifyProviderError("registry execution grant is invalid")
        if not request.actor_id or not request.actor_version:
            raise ApifyProviderError("Actor identity and pinned version are required")
        if not request.requested_source or not request.source_platform:
            raise ApifyProviderError("source scope cannot be verified")
        if (
            isinstance(request.max_cost_usd, bool)
            or not isinstance(request.max_cost_usd, (int, float))
            or not math.isfinite(float(request.max_cost_usd))
            or request.max_cost_usd <= 0
        ):
            raise ApifyProviderError("cost ceiling cannot be verified")
        max_items = request.resource_limits.get("max_dataset_items")
        memory_mbytes = request.resource_limits.get("memory_mbytes")
        if (
            not isinstance(max_items, int)
            or isinstance(max_items, bool)
            or max_items <= 0
        ):
            raise ApifyProviderError("dataset item limit cannot be verified")
        if memory_mbytes is not None and (
            not isinstance(memory_mbytes, int)
            or isinstance(memory_mbytes, bool)
            or memory_mbytes <= 0
        ):
            raise ApifyProviderError("memory limit cannot be verified")

    def estimate_cost(self, request: ProviderAcquisitionRequest) -> CostEstimate:
        self.validate_request(request)
        return CostEstimate(
            amount_usd=float(request.max_cost_usd),
            is_hard_ceiling=True,
            basis="provider-enforced-max-total-charge",
            metadata={"currency": "USD", "provider": self.provider_name},
        )

    def start_run(self, request: ProviderAcquisitionRequest) -> ProviderRunHandle:
        self.validate_request(request)
        if not self._grant_verifier(request, True):
            raise ApifyProviderError(
                "registry execution grant is invalid or already used"
            )
        max_items = request.resource_limits["max_dataset_items"]
        kwargs: dict[str, Any] = {
            "run_input": request.actor_input,
            "build": request.actor_version,
            "max_items": max_items,
            "max_total_charge_usd": Decimal(str(request.max_cost_usd)),
            "run_timeout": timedelta(seconds=request.timeout_seconds),
            "restart_on_error": False,
            "wait_for_finish": 0,
        }
        memory_mbytes = request.resource_limits.get("memory_mbytes")
        if memory_mbytes is not None:
            kwargs["memory_mbytes"] = memory_mbytes
        raw_run = self._client.actor(request.actor_id).start(**kwargs)
        run: dict[str, Any] | None = None
        try:
            run = _normalize_run_response(raw_run, "Apify start response")
            return self._handle_from_run(run, request)
        except Exception:
            run_id = run.get("id") if run is not None else None
            if isinstance(run_id, str) and run_id:
                try:
                    self._client.run(run_id).abort(gracefully=True)
                except Exception:
                    pass
            raise

    def get_run_status(self, handle: ProviderRunHandle) -> ProviderRunStatus:
        self._validate_handle(handle)
        raw_run = self._client.run(handle.run_id).get()
        run = _normalize_run_response(raw_run, "Apify run status")
        run_id = run.get("id")
        if not isinstance(run_id, str) or run_id != handle.run_id:
            raise ApifyProviderError("Apify run status identity cannot be verified")
        self._verify_run_identity(run, handle.actor_id, handle.actor_version)
        state = self._state(run.get("status"))
        dataset_ref = run.get("defaultDatasetId")
        if dataset_ref is not None and not isinstance(dataset_ref, str):
            raise ApifyProviderError("Apify dataset identity cannot be verified")
        cost_final = state not in {ProviderRunState.PENDING, ProviderRunState.RUNNING}
        raw_total_usd = run.get("usageTotalUsd")
        total_usd = (
            None
            if raw_total_usd is None and not cost_final
            else _finite_cost(raw_total_usd)
        )
        checked_at = self._now().isoformat()
        return ProviderRunStatus(
            handle=handle,
            state=state,
            checked_at=checked_at,
            dataset_ref=dataset_ref,
            cost_metadata={
                "total_usd": total_usd,
                "cost_final": cost_final,
                "usage_usd": run.get("usageUsd", {}),
                "compute_units": run.get("stats", {}).get("computeUnits"),
            },
            execution_metadata={
                "status": run.get("status"),
                "build_id": run.get("buildId"),
                "build_number": run.get("buildNumber"),
                "finished_at": (
                    _iso(run.get("finishedAt"), "Actor finish timestamp")
                    if state is ProviderRunState.SUCCEEDED
                    else None
                ),
                "stats": run.get("stats", {}),
                "charged_event_counts": run.get("chargedEventCounts", {}),
                "correlation_id": handle.metadata.get("correlation_id"),
            },
            collection_errors=(),
        )

    def fetch_dataset(self, handle: ProviderRunHandle) -> RawAcquisitionRecord:
        status = self.get_run_status(handle)
        if status.state is not ProviderRunState.SUCCEEDED:
            raise ApifyProviderError(
                "dataset is unavailable before successful execution"
            )
        dataset_ref = status.dataset_ref or handle.dataset_ref
        if not dataset_ref:
            raise ApifyProviderError("Apify dataset identity cannot be verified")
        max_items = handle.metadata.get("max_dataset_items")
        if not isinstance(max_items, int) or max_items <= 0:
            raise ApifyProviderError("dataset item limit cannot be verified")
        page = self._client.dataset(dataset_ref).list_items(
            clean=True, limit=max_items + 1
        )
        items = getattr(page, "items", None)
        if not isinstance(items, list):
            raise ApifyProviderError("Apify dataset payload cannot be verified")
        if len(items) > max_items:
            raise ApifyProviderError("Apify dataset item limit was exceeded")
        return RawAcquisitionRecord(
            provider_name=self.provider_name,
            actor_id=handle.actor_id,
            actor_version=handle.actor_version,
            run_id=handle.run_id,
            dataset_ref=dataset_ref,
            source_identifier=str(handle.metadata["requested_source"]),
            source_platform=str(handle.metadata["source_platform"]),
            retrieved_at=self._now().isoformat(),
            executed_at=handle.started_at,
            payload=items,
            cost_metadata=status.cost_metadata,
            collection_errors=status.collection_errors,
            execution_metadata=status.execution_metadata,
        )

    def cancel_run(self, handle: ProviderRunHandle) -> None:
        self._validate_handle(handle)
        raw_run = self._client.run(handle.run_id).abort(gracefully=True)
        run = _normalize_run_response(raw_run, "Apify cancellation response")
        run_id = run.get("id")
        if not isinstance(run_id, str) or run_id != handle.run_id:
            raise ApifyProviderError("Apify cancellation identity cannot be verified")
        cancellation_status = run.get("status")
        if cancellation_status not in {"ABORTING", "ABORTED"}:
            raise ApifyProviderError("Apify cancellation state cannot be verified")

    def _handle_from_run(
        self, run: dict[str, Any], request: ProviderAcquisitionRequest
    ) -> ProviderRunHandle:
        self._verify_run_identity(run, request.actor_id, request.actor_version)
        run_id = run.get("id")
        if not isinstance(run_id, str) or not run_id:
            raise ApifyProviderError("Apify run identity cannot be verified")
        dataset_ref = run.get("defaultDatasetId")
        if dataset_ref is not None and not isinstance(dataset_ref, str):
            raise ApifyProviderError("Apify dataset identity cannot be verified")
        return ProviderRunHandle(
            provider_name=self.provider_name,
            run_id=run_id,
            actor_id=request.actor_id,
            actor_version=request.actor_version,
            started_at=_iso(run.get("startedAt"), "Actor start timestamp"),
            dataset_ref=dataset_ref,
            metadata={
                "requested_source": request.requested_source,
                "source_platform": request.source_platform,
                "correlation_id": request.correlation_id,
                "max_dataset_items": request.resource_limits["max_dataset_items"],
            },
        )

    def _verify_run_identity(
        self, run: dict[str, Any], actor_id: str, actor_version: str
    ) -> None:
        if run.get("actId") != actor_id:
            raise ApifyProviderError("Apify run did not use the registered Actor")
        if run.get("buildNumber") != actor_version:
            raise ApifyProviderError("Apify run did not use the pinned build")

    def _validate_handle(self, handle: ProviderRunHandle) -> None:
        if handle.provider_name != self.provider_name or not handle.run_id:
            raise ApifyProviderError("provider run handle is invalid")

    @staticmethod
    def _state(value: Any) -> ProviderRunState:
        mapping = {
            "READY": ProviderRunState.PENDING,
            "RUNNING": ProviderRunState.RUNNING,
            "TIMING-OUT": ProviderRunState.RUNNING,
            "ABORTING": ProviderRunState.RUNNING,
            "SUCCEEDED": ProviderRunState.SUCCEEDED,
            "FAILED": ProviderRunState.FAILED,
            "ABORTED": ProviderRunState.CANCELLED,
            "TIMED-OUT": ProviderRunState.TIMED_OUT,
        }
        try:
            return mapping[str(value)]
        except KeyError as exc:
            raise ApifyProviderError("Apify run state cannot be verified") from exc

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None:
            raise ApifyProviderError("Apify adapter clock cannot be verified")
        return value.astimezone(timezone.utc)
