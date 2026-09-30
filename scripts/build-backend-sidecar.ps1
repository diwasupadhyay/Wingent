$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$targetTriple = 'x86_64-pc-windows-msvc'
$binaryName = 'wingent-backend-' + $targetTriple

Set-Location $root
python -m PyInstaller --noconfirm --clean --onefile --name $binaryName --paths backend --distpath src-tauri/binaries --workpath .build/pyinstaller --specpath .build backend/sidecar.py
Write-Host ('Built src-tauri/binaries/' + $binaryName + '.exe')
