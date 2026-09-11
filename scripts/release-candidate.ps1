$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv-sprint\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = 'python' }
& $python (Join-Path $PSScriptRoot 'release_candidate.py') @args
exit $LASTEXITCODE
