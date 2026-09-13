from valo_kernel.relaion_pc_bootstrap import (
    DeviceCapabilities,
    ReadyState,
    choose_local_route,
    evaluate_ready,
    governance_negative_self_test,
)


def test_prefers_npu_local_route() -> None:
    hardware = DeviceCapabilities(
        windows=True,
        architecture="ARM64",
        has_npu=True,
        has_gpu=True,
        memory_gb=16,
    )
    assert choose_local_route(hardware) == "windows-npu-local"


def test_falls_back_to_gpu_then_cpu() -> None:
    gpu = DeviceCapabilities(True, "x64", False, True, 16)
    cpu = DeviceCapabilities(True, "x64", False, False, 16)
    assert choose_local_route(gpu) == "windows-gpu-local"
    assert choose_local_route(cpu) == "windows-cpu-local"


def test_low_memory_has_no_local_route() -> None:
    hardware = DeviceCapabilities(True, "x64", True, True, 4)
    assert choose_local_route(hardware) is None


def test_denied_effect_is_contained_and_receipted() -> None:
    contained, receipt_ok = governance_negative_self_test()
    assert contained is True
    assert receipt_ok is True


def test_supported_machine_becomes_ready() -> None:
    result = evaluate_ready(
        machine_guid="pilot-machine-guid",
        hardware=DeviceCapabilities(True, "ARM64", True, True, 16),
    )
    assert result.state is ReadyState.READY
    assert result.governance_gate is True
    assert result.denied_effect_contained is True
    assert result.receipt_ok is True
    assert result.inference_route == "windows-npu-local"


def test_missing_local_runtime_is_limited_not_ready() -> None:
    result = evaluate_ready(
        machine_guid="pilot-machine-guid",
        hardware=DeviceCapabilities(True, "x64", False, False, 4),
    )
    assert result.state is ReadyState.LIMITED
    assert "NO_LOCAL_INFERENCE_ROUTE" in result.reasons


def test_non_windows_never_becomes_ready() -> None:
    result = evaluate_ready(
        machine_guid="pilot-machine-guid",
        hardware=DeviceCapabilities(False, "x64", False, False, 16),
    )
    assert result.state is ReadyState.NOT_READY
    assert "WINDOWS_REQUIRED" in result.reasons
