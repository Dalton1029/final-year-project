$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Install Python dependencies in .venv first; see README.md.' }
if (-not (Test-Path -LiteralPath 'frontend\dist\index.html')) { throw 'Build the frontend first: cd frontend then npm run build. See README.md.' }
Write-Host 'BenefitLens: http://127.0.0.1:8090/ (keep this terminal running; Ctrl+C stops it)'
& $pythonPath -m uvicorn app.main:app --host 127.0.0.1 --port 8090
exit $LASTEXITCODE
