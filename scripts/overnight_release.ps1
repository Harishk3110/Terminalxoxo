$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'release-candidate.ps1') @args
exit $LASTEXITCODE
