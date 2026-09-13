"""
VAIG Embedded — Hardware Auto-Detection
Detects: Apple Silicon (NEON), NVIDIA (CUDA), Intel (AVX), Qualcomm (Hexagon)
"""
import platform
import subprocess
from enum import Enum

class HWAccel(Enum):
    NONE = "none"
    APPLE_SILICON = "apple_silicon"  # NEON, AMX
    NVIDIA_CUDA = "nvidia_cuda"       # GPU
    INTEL_AVX = "intel_avx"           # AVX-512
    QUALCOMM_HVX = "qualcomm_hvx"     # Hexagon

def detect_hardware() -> HWAccel:
    """Auto-detect available hardware acceleration."""
    system = platform.system()
    machine = platform.machine()

    # Apple Silicon
    if system == "Darwin" and machine == "arm64":
        return HWAccel.APPLE_SILICON

    # NVIDIA
    try:
        result = subprocess.run(["nvidia-smi"], capture_output=True, timeout=2)
        if result.returncode == 0:
            return HWAccel.NVIDIA_CUDA
    except:
        pass

    # Intel AVX-512
    if system in ("Linux", "Windows") and machine in ("x86_64", "AMD64"):
        try:
            with open("/proc/cpuinfo") as f:
                cpuinfo = f.read()
                if "avx512" in cpuinfo.lower():
                    return HWAccel.INTEL_AVX
        except:
            pass

    # Qualcomm (Android/Windows on ARM)
    if machine == "aarch64":
        return HWAccel.QUALCOMM_HVX

    return HWAccel.NONE

def get_optimal_threads(hw: HWAccel) -> int:
    """Get optimal thread count for detected hardware."""
    import os
    cpu_count = os.cpu_count() or 4

    settings = {
        HWAccel.APPLE_SILICON: min(cpu_count, 8),   # P-cores
        HWAccel.NVIDIA_CUDA: min(cpu_count, 16),
        HWAccel.INTEL_AVX: min(cpu_count, 8),
        HWAccel.QUALCOMM_HVX: min(cpu_count, 6),
        HWAccel.NONE: max(1, cpu_count - 1),
    }
    return settings.get(hw, 2)
