$ErrorActionPreference = 'Stop'
Set-Location ($PSScriptRoot + '\..\backend')
$Env:PYTHONPATH = ($PSScriptRoot + '\..\backend')
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
