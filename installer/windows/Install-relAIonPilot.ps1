$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Fail([string]$Message) {
    Write-Host ""
    Write-Host "relAIon was not activated." -ForegroundColor Red
    Write-Host $Message -ForegroundColor Red
    exit 1
}

function Step([string]$Message) {
    Write-Host "[relAIon] $Message" -ForegroundColor Cyan
}

if ($env:OS -ne 'Windows_NT') { Fail 'Windows is required.' }

$installRoot = Join-Path $env:LOCALAPPDATA 'relAIon'
$stateRoot = Join-Path $env:LOCALAPPDATA 'relAIon\state'
$logRoot = Join-Path $env:LOCALAPPDATA 'relAIon\logs'
New-Item -ItemType Directory -Force -Path $installRoot, $stateRoot, $logRoot | Out-Null

Step 'Checking this PC'
$os = Get-CimInstance Win32_OperatingSystem
$computer = Get-CimInstance Win32_ComputerSystem
$memoryGb = [math]::Round($computer.TotalPhysicalMemory / 1GB, 1)
$arch = $env:PROCESSOR_ARCHITECTURE

if ($os.Version -notmatch '^10\.') { Fail "Unsupported Windows version: $($os.Version)" }
if ([Environment]::OSVersion.Version.Build -lt 26100) { Fail 'Windows 11 24H2 build 26100 or later is required.' }
if ($memoryGb -lt 8) { Fail "At least 8 GB RAM is required for the local pilot. Detected: $memoryGb GB." }

$gpu = @(Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue)
$hasGpu = $gpu.Count -gt 0
$npuHints = @(Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue | Where-Object {
    $_.FriendlyName -match 'NPU|Neural|AI Boost|Hexagon|XDNA'
})
$hasNpuHint = $npuHints.Count -gt 0

Step 'Creating local device state'
$machineGuidPath = 'HKLM:\SOFTWARE\Microsoft\Cryptography'
try {
    $machineGuid = (Get-ItemProperty -Path $machineGuidPath -Name MachineGuid).MachineGuid
} catch {
    Fail 'Could not establish the local device identity.'
}
$deviceMaterial = "$machineGuid|$arch"
$sha = [System.Security.Cryptography.SHA256]::Create()
$deviceId = ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($deviceMaterial)))).Replace('-', '').ToLowerInvariant()

Step 'Checking bundled relAIon runtime'
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$bundledRuntime = Join-Path $repoRoot 'runtime\python.exe'
$runtime = $null
if (Test-Path $bundledRuntime) {
    $runtime = $bundledRuntime
} else {
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($python) { $runtime = $python.Source }
    elseif ($py) { $runtime = $py.Source }
}
if (-not $runtime) {
    Fail 'This package is missing its bundled relAIon runtime. Use a complete pilot bundle.'
}

Step 'Installing and proving local AI'
$foundryBootstrap = Join-Path $PSScriptRoot 'Bootstrap-FoundryLocal.ps1'
if (-not (Test-Path $foundryBootstrap)) { Fail 'Foundry Local bootstrap component is missing.' }
try {
    $localAI = & $foundryBootstrap
} catch {
    Fail "Local AI bootstrap failed: $($_.Exception.Message)"
}
if (-not $localAI.inference_verified) { Fail 'Local inference could not be proven.' }

Step 'Running Handlingsrett negative self-test'
$env:PYTHONPATH = Join-Path $repoRoot 'src'
$selfTest = @'
from valo_kernel.relaion_pc_bootstrap import DeviceCapabilities, evaluate_ready
import json, os, sys
h = DeviceCapabilities(
    windows=True,
    architecture=os.environ.get("PROCESSOR_ARCHITECTURE", "unknown"),
    has_npu=os.environ.get("RELAION_NPU_HINT", "0") == "1",
    has_gpu=os.environ.get("RELAION_GPU_HINT", "0") == "1",
    memory_gb=float(os.environ["RELAION_MEMORY_GB"]),
)
r = evaluate_ready(machine_guid=os.environ["RELAION_MACHINE_GUID"], hardware=h)
print(json.dumps({
    "state": r.state.value,
    "device_id": r.device_id,
    "inference_route": r.inference_route,
    "governance_gate": r.governance_gate,
    "denied_effect_contained": r.denied_effect_contained,
    "receipt_ok": r.receipt_ok,
    "reasons": list(r.reasons),
}))
sys.exit(0 if r.state.value == "READY" else 2)
'@

$env:RELAION_NPU_HINT = if ($hasNpuHint) { '1' } else { '0' }
$env:RELAION_GPU_HINT = if ($hasGpu) { '1' } else { '0' }
$env:RELAION_MEMORY_GB = [string]$memoryGb
$env:RELAION_MACHINE_GUID = $machineGuid

$resultJson = $selfTest | & $runtime -
if ($LASTEXITCODE -ne 0) { Fail "Governance self-test did not reach READY. $resultJson" }

$result = $resultJson | ConvertFrom-Json
if (-not $result.governance_gate -or -not $result.denied_effect_contained -or -not $result.receipt_ok) {
    Fail 'The consequence gate self-test failed. No effectful capability has been enabled.'
}

Step 'Writing READY state'
$ready = [ordered]@{
    state = 'READY'
    device_id = $deviceId
    installed_at = [DateTimeOffset]::Now.ToString('o')
    architecture = $arch
    memory_gb = $memoryGb
    npu_hint = $hasNpuHint
    gpu_detected = $hasGpu
    local_ai = 'VERIFIED'
    local_model = $localAI.model
    local_probe_digest = $localAI.probe_digest
    inference_route = $result.inference_route
    governance_gate = $true
    denied_effect_contained = $true
    receipt_ok = $true
    remote_processing = 'OFF'
}
$ready | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $stateRoot 'ready.json')

Write-Host ""
Write-Host 'relAIon PC: READY' -ForegroundColor Green
Write-Host "Local AI: VERIFIED ($($localAI.model))"
Write-Host "Local route: $($result.inference_route)"
Write-Host 'Handlingsrett gate: ACTIVE'
Write-Host 'Remote processing: OFF'
Write-Host "State: $(Join-Path $stateRoot 'ready.json')"
