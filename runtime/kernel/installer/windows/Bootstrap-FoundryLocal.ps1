param(
    [string[]]$PreferredModels = @('phi-4-mini', 'qwen2.5-0.5b')
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Resolve-Foundry {
    $cmd = Get-Command foundry.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $alias = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\foundry.exe'
    if (Test-Path $alias) { return $alias }
    return $null
}

function Ensure-DotNet9Sdk([string]$Winget) {
    $dotnet = Get-Command dotnet.exe -ErrorAction SilentlyContinue
    if ($dotnet) {
        $sdks = & $dotnet.Source --list-sdks 2>$null
        if ($sdks -match '^9\.') { return }
    }
    & $Winget install --id Microsoft.DotNet.SDK.9 -e --accept-source-agreements --accept-package-agreements | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Microsoft .NET 9 SDK installation failed with exit code $LASTEXITCODE" }
}

$build = [Environment]::OSVersion.Version.Build
if ($build -lt 26100) {
    throw "Foundry Local pilot requires Windows 11 24H2 build 26100 or later. Detected build: $build"
}

$winget = Get-Command winget.exe -ErrorAction SilentlyContinue
if (-not $winget) { throw 'Windows Package Manager (winget) is required to bootstrap Foundry Local.' }
Ensure-DotNet9Sdk $winget.Source

$foundry = Resolve-Foundry
if (-not $foundry) {
    & $winget.Source install --id Microsoft.FoundryLocal -e --accept-source-agreements --accept-package-agreements | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Foundry Local installation failed with exit code $LASTEXITCODE" }
    $foundry = Resolve-Foundry
}

if (-not $foundry) {
    throw 'Foundry Local installed but its command alias is not available in this session.'
}

& $foundry server restart | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Foundry Local server restart failed.' }

$selected = $null
foreach ($model in $PreferredModels) {
    & $foundry model info $model *> $null
    if ($LASTEXITCODE -eq 0) {
        $selected = $model
        break
    }
}
if (-not $selected) { throw 'No supported local chat model alias was found.' }

& $foundry model download $selected | Out-Host
if ($LASTEXITCODE -ne 0) { throw "Could not download local model: $selected" }

$probe = & $foundry complete $selected 'Reply with the single token RELAION_READY.' 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) { throw "Local inference probe failed for $selected" }
if ([string]::IsNullOrWhiteSpace($probe)) { throw 'Local inference returned no output.' }

$sha = [System.Security.Cryptography.SHA256]::Create()
$probeDigest = ([BitConverter]::ToString(
    $sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($probe))
)).Replace('-', '').ToLowerInvariant()

[pscustomobject]@{
    foundry = $foundry
    model = $selected
    inference_verified = $true
    probe_digest = $probeDigest
}
