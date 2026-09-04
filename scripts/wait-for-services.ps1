$ErrorActionPreference = "Stop"

$checks = @(
  "http://127.0.0.1:8000/health/ready",
  "http://127.0.0.1:3000",
  "http://127.0.0.1:3001/overview"
)

foreach ($url in $checks) {
  $ok = $false
  for ($i = 0; $i -lt 60; $i++) {
    try {
      Invoke-WebRequest -UseBasicParsing $url -TimeoutSec 5 *> $null
      $ok = $true
      break
    } catch {
      Start-Sleep -Seconds 2
    }
  }
  if (-not $ok) {
    throw "Timed out waiting for $url"
  }
  Write-Host "Ready: $url"
}
