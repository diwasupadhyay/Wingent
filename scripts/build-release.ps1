param([switch]$Run, [switch]$InstallDependencies)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$releaseDirectory = Join-Path $projectRoot 'src-tauri\target\release'
$appPath = Join-Path $releaseDirectory 'app.exe'
$backendPath = Join-Path $releaseDirectory 'wingent-backend.exe'

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program failed (exit $LASTEXITCODE). Build stopped." }
}

Push-Location $projectRoot
try {
    foreach ($program in @('python', 'npm.cmd', 'cargo')) {
        if (-not (Get-Command $program -ErrorAction SilentlyContinue)) { throw "Missing prerequisite: $program" }
    }
    if ($InstallDependencies) {
        Invoke-Checked 'npm.cmd' @('ci')
        Invoke-Checked 'python' @('-m', 'pip', 'install', '-r', 'backend/requirements.txt', 'pyinstaller==6.16.0')
    }
    # Resolve exact executable paths; never stop an unrelated app/port occupant.
    $owned = Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -in @($appPath, $backendPath) }
    foreach ($process in $owned) {
        $current = Get-Process -Id $process.ProcessId -ErrorAction SilentlyContinue
        if ($current -and $current.Path -in @($appPath, $backendPath)) {
            Stop-Process -InputObject $current -Force
            $current.WaitForExit(10000) | Out-Null
        }
    }
    Write-Host 'Building backend...'
    Invoke-Checked 'powershell.exe' @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $PSScriptRoot 'build-backend-sidecar.ps1'))
    Write-Host 'Building embedded desktop UI and EXE...'
    Invoke-Checked 'npm.cmd' @('run', 'tauri:build', '--', '--no-bundle')
    # Explicitly replace the adjacent sidecar, including non-bundled builds.
    $compiledBackend = Join-Path $projectRoot 'src-tauri\binaries\wingent-backend-x86_64-pc-windows-msvc.exe'
    Copy-Item -LiteralPath $compiledBackend -Destination $backendPath -Force
    if (-not (Test-Path -LiteralPath $appPath) -or -not (Test-Path -LiteralPath $backendPath)) {
        throw 'Build did not produce both app.exe and wingent-backend.exe.'
    }
    Write-Host "Ready: $appPath"
    Write-Host 'Keep wingent-backend.exe beside app.exe.'
    if ($Run) { Start-Process -FilePath $appPath -WindowStyle Hidden }
} finally { Pop-Location }
