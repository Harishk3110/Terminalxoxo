param([switch]$Once, [switch]$ObserveOnly)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root '.venv-sprint\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) { $Python = 'python' }
$Arguments = @((Join-Path $PSScriptRoot 'overnight_watchdog.py'))
if ($Once) { $Arguments += '--once' }
if ($ObserveOnly) { $Arguments += '--observe-only' }
& $Python @Arguments
exit $LASTEXITCODE
