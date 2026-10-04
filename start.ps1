$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Create the environment first: py -3.12 -m venv .venv'
}
& $pythonPath -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)"
if ($LASTEXITCODE -ne 0) {
    throw 'This project uses Python 3.12. Recreate .venv with: py -3.12 -m venv .venv'
}
& $pythonPath -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
exit $LASTEXITCODE
