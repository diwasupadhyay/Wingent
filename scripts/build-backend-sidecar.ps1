$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$targetTriple = 'x86_64-pc-windows-msvc'
$binaryName = 'wingent-backend-' + $targetTriple

Set-Location $root
$upstreamLicense = (Join-Path $root 'backend\vendor\self_operating_computer\LICENSE') + ';licenses/self-operating-computer'
python -m PyInstaller --noconfirm --clean --onefile --name $binaryName --paths backend --add-data $upstreamLicense --distpath src-tauri/binaries --workpath .build/pyinstaller --specpath .build backend/sidecar.py
if ($LASTEXITCODE -ne 0) { throw 'Backend sidecar compilation failed.' }
Write-Host ('Built src-tauri/binaries/' + $binaryName + '.exe')
