param(
  [ValidateSet("backup", "verify", "restore-test")]
  [string]$Action = "backup",
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$BackupArguments
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv-sprint\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) { $python = "python" }
Push-Location -LiteralPath $root
try {
  & $python -m infrastructure.scripts.managed_backup $Action @BackupArguments
  $code = $LASTEXITCODE
} finally {
  Pop-Location
}
exit $code
