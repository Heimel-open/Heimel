"""Provider-neutral semantic routing for VALO Factory.

Routing is advisory selection only. It has no authority surface and performs no
execution. REHT remains the execution authorization boundary.
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping, Protocol, Sequence


AUTHORITY_EFFECT = "none"
DEFAULT_ROUTER_VERSION = "0.1.30"


class RouterError(RuntimeError):
    pass


class RouterValidationError(RouterError):
    pass


class RouterUnavailableError(RouterError):
    pass


@dataclass(frozen=True)
class RoutingCandidate:
    route_id: str
    handler: str
    embedding: tuple[float, ...]
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class RoutingRequest:
    task_id: str
    query_embedding: tuple[float, ...]
    candidates: tuple[RoutingCandidate, ...]
    k: int = 1
    threshold: float = 0.7
    metric: str = "cosine"


@dataclass(frozen=True)
class RouteSuggestion:
    route_id: str
    handler: str
    score: float
    metadata: Mapping[str, object] = field(default_factory=dict)
    authority_effect: str = AUTHORITY_EFFECT

    def as_dict(self) -> dict:
        return {
            "route_id": self.route_id,
            "handler": self.handler,
            "score": self.score,
            "metadata": dict(self.metadata),
            "authority_effect": self.authority_effect,
        }


@dataclass(frozen=True)
class RoutingReceipt:
    task_id: str
    request_digest: str
    router_id: str
    router_version: str
    suggestions: tuple[RouteSuggestion, ...]
    authority_effect: str = AUTHORITY_EFFECT

    def as_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "request_digest": self.request_digest,
            "router_id": self.router_id,
            "router_version": self.router_version,
            "suggestions": [item.as_dict() for item in self.suggestions],
            "authority_effect": self.authority_effect,
        }


class RouterAdapter(Protocol):
    router_id: str

    def route(self, request: RoutingRequest) -> RoutingReceipt:
        ...


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


def _default_runner(
    argv: Sequence[str],
    *,
    input_text: str,
    cwd: str | None = None,
    timeout: float | None = None,
) -> CommandResult:
    try:
        proc = subprocess.run(
            list(argv),
            input=input_text,
            text=True,
            capture_output=True,
            cwd=cwd,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RouterUnavailableError(f"{argv[0]} is not installed") from exc
    return CommandResult(proc.returncode, proc.stdout, proc.stderr)


def _as_finite_vector(values: Sequence[object], field_name: str) -> tuple[float, ...]:
    if isinstance(values, (str, bytes)) or not values:
        raise RouterValidationError(f"{field_name} must be a non-empty numeric vector")
    vector = []
    for value in values:
        if isinstance(value, bool):
            raise RouterValidationError(f"{field_name} contains a non-numeric value")
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise RouterValidationError(
                f"{field_name} contains a non-numeric value"
            ) from exc
        if not math.isfinite(number):
            raise RouterValidationError(f"{field_name} contains a non-finite value")
        vector.append(number)
    return tuple(vector)


def validate_request(request: RoutingRequest) -> int:
    if not request.task_id.strip():
        raise RouterValidationError("task_id must not be empty")
    query = _as_finite_vector(request.query_embedding, "query_embedding")
    if not request.candidates:
        raise RouterValidationError("at least one routing candidate is required")
    if request.k < 1 or request.k > len(request.candidates):
        raise RouterValidationError("k must be between 1 and candidate count")
    if not 0.0 <= request.threshold <= 1.0:
        raise RouterValidationError("threshold must be between 0 and 1")
    if request.metric != "cosine":
        raise RouterValidationError("only cosine routing is admitted")
    dimension = len(query)
    route_ids: set[str] = set()
    for candidate in request.candidates:
        if not candidate.route_id.strip() or not candidate.handler.strip():
            raise RouterValidationError("candidate route_id and handler are required")
        if candidate.route_id in route_ids:
            raise RouterValidationError(f"duplicate route_id: {candidate.route_id}")
        route_ids.add(candidate.route_id)
        embedding = _as_finite_vector(
            candidate.embedding, f"candidate[{candidate.route_id}].embedding"
        )
        if len(embedding) != dimension:
            raise RouterValidationError(
                f"dimension mismatch for candidate {candidate.route_id}: "
                f"expected {dimension}, got {len(embedding)}"
            )
    return dimension


def _request_payload(request: RoutingRequest) -> dict:
    dimension = validate_request(request)
    return {
        "task_id": request.task_id,
        "dimension": dimension,
        "metric": request.metric,
        "threshold": request.threshold,
        "k": request.k,
        "query_embedding": list(request.query_embedding),
        "candidates": [
            {
                "route_id": item.route_id,
                "handler": item.handler,
                "embedding": list(item.embedding),
                "metadata": dict(item.metadata),
            }
            for item in request.candidates
        ],
    }


def _digest_payload(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


class RuVectorRouterAdapter:
    router_id = "ruvector"

    def __init__(
        self,
        *,
        connector_path: str | Path | None = None,
        node_binary: str = "node",
        runner: Callable[..., CommandResult] = _default_runner,
        timeout: float = 10.0,
    ) -> None:
        root = Path(__file__).resolve().parents[1]
        self.connector_path = Path(
            connector_path or root / "connectors" / "ruvector" / "router.cjs"
        )
        self.node_binary = node_binary
        self.runner = runner
        self.timeout = timeout

    def route(self, request: RoutingRequest) -> RoutingReceipt:
        payload = _request_payload(request)
        request_digest = _digest_payload(payload)
        result = self.runner(
            (self.node_binary, str(self.connector_path)),
            input_text=json.dumps(payload, separators=(",", ":")),
            cwd=str(self.connector_path.parent),
            timeout=self.timeout,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()[:500]
            raise RouterError(
                f"ruvector connector failed rc={result.returncode}: {detail}"
            )
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RouterValidationError("router returned invalid JSON") from exc
        suggestions, version = self._validate_output(output, request)
        return RoutingReceipt(
            task_id=request.task_id,
            request_digest=request_digest,
            router_id=self.router_id,
            router_version=version,
            suggestions=tuple(suggestions),
        )

    @staticmethod
    def _validate_output(
        output: object, request: RoutingRequest
    ) -> tuple[list[RouteSuggestion], str]:
        if not isinstance(output, dict):
            raise RouterValidationError("router output must be an object")
        allowed_top = {"router_id", "router_version", "authority_effect", "results"}
        extra_top = set(output) - allowed_top
        if extra_top:
            raise RouterValidationError(
                f"router output contains unsupported fields: {sorted(extra_top)}"
            )
        if output.get("router_id") != "ruvector":
            raise RouterValidationError("unexpected router_id")
        if output.get("authority_effect") != AUTHORITY_EFFECT:
            raise RouterValidationError("router attempted to carry authority")
        version = output.get("router_version")
        if version != DEFAULT_ROUTER_VERSION:
            raise RouterValidationError(
                f"unexpected router_version: {version!r}"
            )
        results = output.get("results")
        if not isinstance(results, list):
            raise RouterValidationError("router results must be a list")
        if len(results) > request.k:
            raise RouterValidationError("router returned more results than requested")

        expected = {item.route_id: item for item in request.candidates}
        suggestions: list[RouteSuggestion] = []
        seen: set[str] = set()
        for raw in results:
            if not isinstance(raw, dict):
                raise RouterValidationError("router result must be an object")
            allowed_result = {"route_id", "handler", "score", "metadata"}
            extra = set(raw) - allowed_result
            if extra:
                raise RouterValidationError(
                    f"router result contains unsupported fields: {sorted(extra)}"
                )
            route_id = raw.get("route_id")
            handler = raw.get("handler")
            if not isinstance(route_id, str) or route_id not in expected:
                raise RouterValidationError("router returned an unknown route_id")
            if route_id in seen:
                raise RouterValidationError("router returned duplicate route_id")
            seen.add(route_id)
            if handler != expected[route_id].handler:
                raise RouterValidationError("router changed candidate handler")
            score = raw.get("score")
            if isinstance(score, bool) or not isinstance(score, (int, float)):
                raise RouterValidationError("router score must be numeric")
            score = float(score)
            if not math.isfinite(score) or not 0.0 <= score <= 1.0:
                raise RouterValidationError("router score must be finite and in [0, 1]")
            if score < request.threshold:
                raise RouterValidationError("router returned a score below threshold")
            metadata = raw.get("metadata", {})
            if not isinstance(metadata, dict):
                raise RouterValidationError("router metadata must be an object")
            expected_metadata = dict(expected[route_id].metadata)
            if metadata != expected_metadata:
                raise RouterValidationError("router changed candidate metadata")
            suggestions.append(
                RouteSuggestion(
                    route_id=route_id,
                    handler=handler,
                    score=score,
                    metadata=expected_metadata,
                )
            )
        return suggestions, version


class RouterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, RouterAdapter] = {}

    def register(self, adapter: RouterAdapter, *, replace: bool = False) -> None:
        router_id = getattr(adapter, "router_id", "")
        if not isinstance(router_id, str) or not router_id:
            raise RouterValidationError("adapter router_id is required")
        if router_id in self._adapters and not replace:
            raise RouterValidationError(f"router already registered: {router_id}")
        self._adapters[router_id] = adapter

    def get(self, router_id: str) -> RouterAdapter:
        try:
            return self._adapters[router_id]
        except KeyError as exc:
            raise RouterValidationError(f"unknown router: {router_id}") from exc

    def route(self, router_id: str, request: RoutingRequest) -> RoutingReceipt:
        return self.get(router_id).route(request)


def request_from_dict(data: Mapping[str, object]) -> RoutingRequest:
    if not isinstance(data, Mapping):
        raise RouterValidationError("request must be an object")
    raw_candidates = data.get("candidates")
    if not isinstance(raw_candidates, list):
        raise RouterValidationError("candidates must be a list")
    candidates = []
    for raw in raw_candidates:
        if not isinstance(raw, Mapping):
            raise RouterValidationError("candidate must be an object")
        metadata = raw.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise RouterValidationError("candidate metadata must be an object")
        candidates.append(
            RoutingCandidate(
                route_id=str(raw.get("route_id", "")),
                handler=str(raw.get("handler", "")),
                embedding=_as_finite_vector(
                    raw.get("embedding", ()), "candidate.embedding"
                ),
                metadata=dict(metadata),
            )
        )
    request = RoutingRequest(
        task_id=str(data.get("task_id", "")),
        query_embedding=_as_finite_vector(
            data.get("query_embedding", ()), "query_embedding"
        ),
        candidates=tuple(candidates),
        k=int(data.get("k", 1)),
        threshold=float(data.get("threshold", 0.7)),
        metric=str(data.get("metric", "cosine")),
    )
    validate_request(request)
    return request
