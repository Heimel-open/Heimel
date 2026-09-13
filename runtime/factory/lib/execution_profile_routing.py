"""Hardware-neutral completion-first execution-profile routing.

This module only suggests an execution profile. It cannot execute work or grant
authority. Verified completion evidence is the primary ranking signal; raw
provider/CLI success is not treated as correctness.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Mapping, Sequence

AUTHORITY_EFFECT = "none"
SELECTOR_ID = "valo.execution-profile-router"
SELECTOR_VERSION = "1.0.0"

VERIFIED_COMPLETE = "VERIFIED_COMPLETE"
VERIFIED_INCOMPLETE = "VERIFIED_INCOMPLETE"
UNVERIFIED = "UNVERIFIED"
_ALLOWED_OUTCOMES = {VERIFIED_COMPLETE, VERIFIED_INCOMPLETE, UNVERIFIED}


class ExecutionProfileRoutingError(ValueError):
    pass


@dataclass(frozen=True)
class ExecutionProfile:
    profile_id: str
    handler: str
    provider_id: str
    harness_id: str
    runtime_id: str
    model_id: str
    sandbox_id: str
    quantization: str = "provider_default"
    cache_strategy: str = "provider_default"
    capabilities: tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)
    authority_effect: str = AUTHORITY_EFFECT

    def as_dict(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "handler": self.handler,
            "provider_id": self.provider_id,
            "harness_id": self.harness_id,
            "runtime_id": self.runtime_id,
            "model_id": self.model_id,
            "sandbox_id": self.sandbox_id,
            "quantization": self.quantization,
            "cache_strategy": self.cache_strategy,
            "capabilities": list(self.capabilities),
            "metadata": dict(self.metadata),
            "authority_effect": self.authority_effect,
        }


@dataclass(frozen=True)
class ProfileObservation:
    observation_id: str
    profile_id: str
    task_class: str
    outcome: str
    execution_receipt_ref: str
    verifier_ref: str | None = None
    latency_ms: int | None = None
    cost_microunits: int | None = None
    authority_effect: str = AUTHORITY_EFFECT

    @property
    def independently_verified(self) -> bool:
        return self.outcome in {VERIFIED_COMPLETE, VERIFIED_INCOMPLETE}


@dataclass(frozen=True)
class ProfileRoutingRequest:
    task_id: str
    task_class: str
    candidates: tuple[ExecutionProfile, ...]
    observations: tuple[ProfileObservation, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    allowed_providers: tuple[str, ...] = ()
    allowed_harnesses: tuple[str, ...] = ()
    allowed_runtimes: tuple[str, ...] = ()
    k: int = 1


@dataclass(frozen=True)
class ProfileSuggestion:
    profile: ExecutionProfile
    completion_score: float
    verified_attempts: int
    verified_completions: int
    avg_latency_ms: float | None
    avg_cost_microunits: float | None
    evidence_digest: str
    authority_effect: str = AUTHORITY_EFFECT

    def as_dict(self) -> dict:
        return {
            "profile": self.profile.as_dict(),
            "completion_score": self.completion_score,
            "verified_attempts": self.verified_attempts,
            "verified_completions": self.verified_completions,
            "avg_latency_ms": self.avg_latency_ms,
            "avg_cost_microunits": self.avg_cost_microunits,
            "evidence_digest": self.evidence_digest,
            "authority_effect": self.authority_effect,
        }


@dataclass(frozen=True)
class ProfileRoutingReceipt:
    task_id: str
    task_class: str
    request_digest: str
    selector_id: str
    selector_version: str
    suggestions: tuple[ProfileSuggestion, ...]
    authority_effect: str = AUTHORITY_EFFECT

    def as_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "task_class": self.task_class,
            "request_digest": self.request_digest,
            "selector_id": self.selector_id,
            "selector_version": self.selector_version,
            "suggestions": [item.as_dict() for item in self.suggestions],
            "authority_effect": self.authority_effect,
        }


def _digest(payload: object) -> str:
    try:
        raw = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ExecutionProfileRoutingError(
            "routing payload must be deterministically JSON serializable"
        ) from exc
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ExecutionProfileRoutingError(f"{field_name} must not be empty")


def _validate_profile(profile: ExecutionProfile) -> None:
    for field_name in (
        "profile_id", "handler", "provider_id", "harness_id", "runtime_id",
        "model_id", "sandbox_id", "quantization", "cache_strategy",
    ):
        _require_text(getattr(profile, field_name), f"profile.{field_name}")
    if profile.authority_effect != AUTHORITY_EFFECT:
        raise ExecutionProfileRoutingError("execution profile attempted to carry authority")
    if len(set(profile.capabilities)) != len(profile.capabilities):
        raise ExecutionProfileRoutingError(
            f"duplicate capability in profile {profile.profile_id}"
        )
    for capability in profile.capabilities:
        _require_text(capability, "profile.capability")
    _digest(profile.as_dict())


def _validate_observation(observation: ProfileObservation) -> None:
    for field_name in ("observation_id", "profile_id", "task_class", "execution_receipt_ref"):
        _require_text(getattr(observation, field_name), f"observation.{field_name}")
    if observation.outcome not in _ALLOWED_OUTCOMES:
        raise ExecutionProfileRoutingError(f"unsupported outcome: {observation.outcome}")
    if observation.authority_effect != AUTHORITY_EFFECT:
        raise ExecutionProfileRoutingError("observation attempted to carry authority")
    if observation.independently_verified:
        if not observation.verifier_ref:
            raise ExecutionProfileRoutingError(
                "verified outcomes require an independent verifier_ref"
            )
    elif observation.verifier_ref:
        raise ExecutionProfileRoutingError(
            "UNVERIFIED outcome must not carry verifier_ref"
        )
    for field_name in ("latency_ms", "cost_microunits"):
        value = getattr(observation, field_name)
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, int) or value < 0
        ):
            raise ExecutionProfileRoutingError(
                f"observation.{field_name} must be a non-negative integer or null"
            )


def validate_request(request: ProfileRoutingRequest) -> None:
    _require_text(request.task_id, "task_id")
    _require_text(request.task_class, "task_class")
    if not request.candidates:
        raise ExecutionProfileRoutingError("at least one execution profile is required")
    if request.k < 1:
        raise ExecutionProfileRoutingError("k must be at least 1")
    ids: set[str] = set()
    for profile in request.candidates:
        _validate_profile(profile)
        if profile.profile_id in ids:
            raise ExecutionProfileRoutingError(
                f"duplicate profile_id: {profile.profile_id}"
            )
        ids.add(profile.profile_id)
    for observation in request.observations:
        _validate_observation(observation)
        if observation.profile_id not in ids:
            raise ExecutionProfileRoutingError(
                f"observation references unknown profile: {observation.profile_id}"
            )
    for group_name in (
        "required_capabilities", "allowed_providers", "allowed_harnesses",
        "allowed_runtimes",
    ):
        values = getattr(request, group_name)
        if len(set(values)) != len(values):
            raise ExecutionProfileRoutingError(f"duplicate value in {group_name}")
        for value in values:
            _require_text(value, group_name)


def _request_payload(request: ProfileRoutingRequest) -> dict:
    return {
        "task_id": request.task_id,
        "task_class": request.task_class,
        "candidates": [item.as_dict() for item in request.candidates],
        "observations": [
            {
                "observation_id": item.observation_id,
                "profile_id": item.profile_id,
                "task_class": item.task_class,
                "outcome": item.outcome,
                "execution_receipt_ref": item.execution_receipt_ref,
                "verifier_ref": item.verifier_ref,
                "latency_ms": item.latency_ms,
                "cost_microunits": item.cost_microunits,
                "authority_effect": item.authority_effect,
            }
            for item in request.observations
        ],
        "required_capabilities": list(request.required_capabilities),
        "allowed_providers": list(request.allowed_providers),
        "allowed_harnesses": list(request.allowed_harnesses),
        "allowed_runtimes": list(request.allowed_runtimes),
        "k": request.k,
    }


def _admissible(profile: ExecutionProfile, request: ProfileRoutingRequest) -> bool:
    if not set(request.required_capabilities).issubset(profile.capabilities):
        return False
    if request.allowed_providers and profile.provider_id not in request.allowed_providers:
        return False
    if request.allowed_harnesses and profile.harness_id not in request.allowed_harnesses:
        return False
    if request.allowed_runtimes and profile.runtime_id not in request.allowed_runtimes:
        return False
    return True


def _mean(values: Sequence[int]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _suggestion(
    profile: ExecutionProfile,
    observations: Sequence[ProfileObservation],
) -> ProfileSuggestion:
    verified = [item for item in observations if item.independently_verified]
    completed = [item for item in verified if item.outcome == VERIFIED_COMPLETE]
    attempts = len(verified)
    successes = len(completed)

    # Laplace smoothing gives an unseen profile a neutral 0.5 prior. A verified
    # failure moves it below neutral; a verified completion moves it above.
    completion_score = (successes + 1) / (attempts + 2)

    latencies = [item.latency_ms for item in verified if item.latency_ms is not None]
    costs = [
        item.cost_microunits
        for item in verified
        if item.cost_microunits is not None
    ]
    evidence_payload = [
        {
            "observation_id": item.observation_id,
            "outcome": item.outcome,
            "execution_receipt_ref": item.execution_receipt_ref,
            "verifier_ref": item.verifier_ref,
            "latency_ms": item.latency_ms,
            "cost_microunits": item.cost_microunits,
        }
        for item in verified
    ]
    return ProfileSuggestion(
        profile=profile,
        completion_score=completion_score,
        verified_attempts=attempts,
        verified_completions=successes,
        avg_latency_ms=_mean(latencies),
        avg_cost_microunits=_mean(costs),
        evidence_digest=_digest(evidence_payload),
    )


def _rank_key(item: ProfileSuggestion) -> tuple:
    latency = item.avg_latency_ms if item.avg_latency_ms is not None else math.inf
    cost = (
        item.avg_cost_microunits
        if item.avg_cost_microunits is not None
        else math.inf
    )
    return (
        -item.completion_score,
        -item.verified_attempts,
        latency,
        cost,
        item.profile.profile_id,
    )


def route_execution_profiles(request: ProfileRoutingRequest) -> ProfileRoutingReceipt:
    validate_request(request)
    request_digest = _digest(_request_payload(request))
    suggestions: list[ProfileSuggestion] = []
    for profile in request.candidates:
        if not _admissible(profile, request):
            continue
        observations = [
            item
            for item in request.observations
            if item.profile_id == profile.profile_id
            and item.task_class == request.task_class
        ]
        suggestions.append(_suggestion(profile, observations))

    suggestions.sort(key=_rank_key)
    return ProfileRoutingReceipt(
        task_id=request.task_id,
        task_class=request.task_class,
        request_digest=request_digest,
        selector_id=SELECTOR_ID,
        selector_version=SELECTOR_VERSION,
        suggestions=tuple(suggestions[: request.k]),
    )


def _tuple_of_text(value: object, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ExecutionProfileRoutingError(f"{field_name} must be a list")
    if any(not isinstance(item, str) for item in value):
        raise ExecutionProfileRoutingError(f"{field_name} values must be strings")
    return tuple(value)


def _optional_nonnegative_int(value: object, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ExecutionProfileRoutingError(
            f"{field_name} must be a non-negative integer or null"
        )
    return value


def _positive_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ExecutionProfileRoutingError(f"{field_name} must be a positive integer")
    return value


def request_from_dict(data: Mapping[str, object]) -> ProfileRoutingRequest:
    if not isinstance(data, Mapping):
        raise ExecutionProfileRoutingError("request must be an object")

    raw_candidates = data.get("candidates")
    if not isinstance(raw_candidates, list):
        raise ExecutionProfileRoutingError("candidates must be a list")
    candidates: list[ExecutionProfile] = []
    for raw in raw_candidates:
        if not isinstance(raw, Mapping):
            raise ExecutionProfileRoutingError("candidate must be an object")
        metadata = raw.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ExecutionProfileRoutingError("candidate.metadata must be an object")
        candidates.append(ExecutionProfile(
            profile_id=str(raw.get("profile_id", "")),
            handler=str(raw.get("handler", "")),
            provider_id=str(raw.get("provider_id", "")),
            harness_id=str(raw.get("harness_id", "")),
            runtime_id=str(raw.get("runtime_id", "")),
            model_id=str(raw.get("model_id", "")),
            sandbox_id=str(raw.get("sandbox_id", "")),
            quantization=str(raw.get("quantization", "provider_default")),
            cache_strategy=str(raw.get("cache_strategy", "provider_default")),
            capabilities=_tuple_of_text(raw.get("capabilities", []), "capabilities"),
            metadata=dict(metadata),
            authority_effect=str(raw.get("authority_effect", AUTHORITY_EFFECT)),
        ))

    raw_observations = data.get("observations", [])
    if not isinstance(raw_observations, list):
        raise ExecutionProfileRoutingError("observations must be a list")
    observations: list[ProfileObservation] = []
    for raw in raw_observations:
        if not isinstance(raw, Mapping):
            raise ExecutionProfileRoutingError("observation must be an object")
        latency = raw.get("latency_ms")
        cost = raw.get("cost_microunits")
        observations.append(ProfileObservation(
            observation_id=str(raw.get("observation_id", "")),
            profile_id=str(raw.get("profile_id", "")),
            task_class=str(raw.get("task_class", "")),
            outcome=str(raw.get("outcome", "")),
            execution_receipt_ref=str(raw.get("execution_receipt_ref", "")),
            verifier_ref=(
                str(raw["verifier_ref"]) if raw.get("verifier_ref") is not None else None
            ),
            latency_ms=_optional_nonnegative_int(latency, "latency_ms"),
            cost_microunits=_optional_nonnegative_int(cost, "cost_microunits"),
            authority_effect=str(raw.get("authority_effect", AUTHORITY_EFFECT)),
        ))

    request = ProfileRoutingRequest(
        task_id=str(data.get("task_id", "")),
        task_class=str(data.get("task_class", "")),
        candidates=tuple(candidates),
        observations=tuple(observations),
        required_capabilities=_tuple_of_text(
            data.get("required_capabilities", []), "required_capabilities"
        ),
        allowed_providers=_tuple_of_text(
            data.get("allowed_providers", []), "allowed_providers"
        ),
        allowed_harnesses=_tuple_of_text(
            data.get("allowed_harnesses", []), "allowed_harnesses"
        ),
        allowed_runtimes=_tuple_of_text(
            data.get("allowed_runtimes", []), "allowed_runtimes"
        ),
        k=_positive_int(data.get("k", 1), "k"),
    )
    validate_request(request)
    return request


__all__ = [
    "AUTHORITY_EFFECT",
    "ExecutionProfile",
    "ExecutionProfileRoutingError",
    "ProfileObservation",
    "ProfileRoutingReceipt",
    "ProfileRoutingRequest",
    "ProfileSuggestion",
    "UNVERIFIED",
    "VERIFIED_COMPLETE",
    "VERIFIED_INCOMPLETE",
    "request_from_dict",
    "route_execution_profiles",
    "validate_request",
]
