from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Callable

from .contracts.common import canonical_digest
from .windows_capability_adapter import (
    AuthorizationDisposition,
    CommitAuthorization,
    EffectRequest,
    WindowsCapabilitySurface,
    invoke_governed_windows_capability,
)


class ReadyState(StrEnum):
    READY = "READY"
    LIMITED = "LIMITED"
    NOT_READY = "NOT_READY"


@dataclass(frozen=True)
class DeviceCapabilities:
    windows: bool
    architecture: str
    has_npu: bool
    has_gpu: bool
    memory_gb: float


@dataclass(frozen=True)
class BootstrapResult:
    state: ReadyState
    device_id: str
    inference_route: str | None
    governance_gate: bool
    denied_effect_contained: bool
    receipt_ok: bool
    reasons: tuple[str, ...]


HardwareProbe = Callable[[], DeviceCapabilities]
RuntimeProbe = Callable[[DeviceCapabilities], str | None]


def derive_device_id(*, machine_guid: str, architecture: str) -> str:
    if not machine_guid.strip():
        raise ValueError("machine_guid is required")
    return canonical_digest({"machine_guid": machine_guid, "architecture": architecture})


def choose_local_route(capabilities: DeviceCapabilities) -> str | None:
    if not capabilities.windows:
        return None
    if capabilities.memory_gb < 8:
        return None
    if capabilities.has_npu:
        return "windows-npu-local"
    if capabilities.has_gpu:
        return "windows-gpu-local"
    return "windows-cpu-local"


def _effect_request(now: datetime) -> EffectRequest:
    return EffectRequest(
        request_id="relaion-selftest-deny",
        actor_id="relaion-selftest-agent",
        principal_id="local-user",
        surface=WindowsCapabilitySurface.APP_ACTION,
        capability_id="selftest.write",
        provider_id="relaion.selftest.provider",
        target="relaion://selftest/forbidden-effect",
        purpose="prove-denied-effects-do-not-execute",
        mandate_ref="selftest-mandate",
        parameters={"sentinel": "must-not-run"},
        requested_at=now,
    )


def governance_negative_self_test(*, now: datetime | None = None) -> tuple[bool, bool]:
    now = now or datetime.now(UTC)
    request = _effect_request(now)
    provider_called = False

    def authorize(req: EffectRequest, at: datetime) -> CommitAuthorization:
        return CommitAuthorization(
            decision_id="relaion-selftest-deny-decision",
            disposition=AuthorizationDisposition.DENY,
            effect_digest=req.effect_digest,
            evaluated_at=at,
            valid_until=at + timedelta(seconds=5),
            reasons=("SELF_TEST_EXPECTED_DENY",),
            authority_ref="relaion-selftest-authority",
        )

    def provider(_: EffectRequest) -> dict[str, bool]:
        nonlocal provider_called
        provider_called = True
        return {"executed": True}

    receipt = invoke_governed_windows_capability(
        request=request,
        authorize=authorize,
        provider_invoke=provider,
        commit_time=now,
    )
    contained = not provider_called and not receipt.invoked
    receipt_ok = bool(receipt.receipt_digest) and receipt.effect_digest == request.effect_digest
    return contained, receipt_ok


def evaluate_ready(
    *,
    machine_guid: str,
    hardware: DeviceCapabilities,
    runtime_probe: RuntimeProbe = choose_local_route,
) -> BootstrapResult:
    reasons: list[str] = []
    device_id = derive_device_id(machine_guid=machine_guid, architecture=hardware.architecture)

    if not hardware.windows:
        reasons.append("WINDOWS_REQUIRED")

    route = runtime_probe(hardware)
    if route is None:
        reasons.append("NO_LOCAL_INFERENCE_ROUTE")

    denied_effect_contained, receipt_ok = governance_negative_self_test()
    if not denied_effect_contained:
        reasons.append("DENIED_EFFECT_REACHED_PROVIDER")
    if not receipt_ok:
        reasons.append("RECEIPT_SELF_TEST_FAILED")

    governance_gate = denied_effect_contained and receipt_ok

    if not reasons and governance_gate and route is not None:
        state = ReadyState.READY
    elif hardware.windows and governance_gate:
        state = ReadyState.LIMITED
    else:
        state = ReadyState.NOT_READY

    return BootstrapResult(
        state=state,
        device_id=device_id,
        inference_route=route,
        governance_gate=governance_gate,
        denied_effect_contained=denied_effect_contained,
        receipt_ok=receipt_ok,
        reasons=tuple(reasons),
    )


def write_ready_marker(result: BootstrapResult, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "state": result.state.value,
        "device_id": result.device_id,
        "inference_route": result.inference_route,
        "governance_gate": result.governance_gate,
        "denied_effect_contained": result.denied_effect_contained,
        "receipt_ok": result.receipt_ok,
        "reasons": list(result.reasons),
    }
    destination.write_text(str(payload), encoding="utf-8")
