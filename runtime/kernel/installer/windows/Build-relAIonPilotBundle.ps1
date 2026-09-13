param(
    [Parameter(Mandatory=$true)][string]$PythonEmbedUrl,
    [string]$OutputDir = "dist\relaion-pilot"
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$output = Join-Path $repoRoot $OutputDir
$runtime = Join-Path $output 'runtime'
$temp = Join-Path $env:TEMP ('relaion-build-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $output, $runtime, $temp | Out-Null

Write-Host '[relAIon build] Copying application files'
Copy-Item -Recurse -Force (Join-Path $repoRoot 'src') $output
New-Item -ItemType Directory -Force -Path (Join-Path $output 'installer\windows') | Out-Null
Copy-Item -Force (Join-Path $repoRoot 'installer\windows\Install-relAIonPilot.ps1') (Join-Path $output 'installer\windows\Install-relAIonPilot.ps1')
Copy-Item -Force (Join-Path $repoRoot 'installer\windows\Install-relAIonPilot.cmd') (Join-Path $output 'installer\windows\Install-relAIonPilot.cmd')
Copy-Item -Force (Join-Path $repoRoot 'installer\windows\Bootstrap-FoundryLocal.ps1') (Join-Path $output 'installer\windows\Bootstrap-FoundryLocal.ps1')

Write-Host '[relAIon build] Downloading official Python embeddable runtime'
$zip = Join-Path $temp 'python-embed.zip'
Invoke-WebRequest -Uri $PythonEmbedUrl -OutFile $zip
Expand-Archive -Path $zip -DestinationPath $runtime -Force

$pth = Get-ChildItem $runtime -Filter 'python*._pth' | Select-Object -First 1
if (-not $pth) { throw 'Python embeddable _pth file not found.' }
$pthContent = Get-Content $pth.FullName
$pthContent = $pthContent | ForEach-Object {
    if ($_ -eq '#import site') { 'import site' } else { $_ }
}
$pthContent += 'Lib\site-packages'
$pthContent | Set-Content -Encoding ASCII $pth.FullName

Write-Host '[relAIon build] Bootstrapping pip and runtime dependencies'
$getPip = Join-Path $temp 'get-pip.py'
Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile $getPip
& (Join-Path $runtime 'python.exe') $getPip --no-warn-script-location
& (Join-Path $runtime 'python.exe') -m pip install --no-warn-script-location --target (Join-Path $runtime 'Lib\site-packages') `
    'pydantic>=2.6,<3' 'cryptography>=42' 'rfc8785>=0.1.4'

Write-Host '[relAIon build] Writing bundle manifest'
$manifest = [ordered]@{
    product = 'relAIon Pilot'
    built_at = [DateTimeOffset]::Now.ToString('o')
    source = 'nsolland/valo-kernel'
    branch = 'feat/windows-capability-adapter-v0'
    remote_processing_default = 'OFF'
    entrypoint = 'installer\windows\Install-relAIonPilot.cmd'
}
$manifest | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $output 'bundle.json')

$archive = "$output.zip"
if (Test-Path $archive) { Remove-Item -Force $archive }
Compress-Archive -Path (Join-Path $output '*') -DestinationPath $archive
Write-Host "relAIon pilot bundle: $archive"
