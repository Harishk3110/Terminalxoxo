$ErrorActionPreference = "Continue"

$results = @()
$failed = $false
function Run-Step($Name, $Command) {
  Write-Host "== $Name =="
  powershell -NoProfile -ExecutionPolicy Bypass -Command $Command
  $code = $LASTEXITCODE
  $script:results += [PSCustomObject]@{ Name = $Name; ExitCode = $code }
  if ($code -ne 0) {
    Write-Host "FAILED: $Name ($code)"
    $script:failed = $true
  }
}

Run-Step "git status" "git status --short --branch"
Run-Step "python dependencies" "python -m pip install -r services/api/requirements.txt"
Run-Step "javascript dependencies" "corepack pnpm install"
Run-Step "alembic upgrade" "`$env:DATABASE_URL='sqlite:///./knk_acceptance.db'; alembic upgrade head"
Run-Step "demo seed" "`$env:DATABASE_URL='sqlite:///./knk_acceptance.db'; python services/api/scripts/seed_demo.py --reset"
Run-Step "backend tests" "python -m pytest services/api/tests"
Run-Step "frontend typecheck" "corepack pnpm typecheck"
Run-Step "frontend lint" "corepack pnpm lint"
Run-Step "frontend tests and security" "corepack pnpm test"
Run-Step "public build" "corepack pnpm --filter @knk/public-web build"
Run-Step "terminal build" "corepack pnpm --filter @knk/terminal-web build"
Run-Step "e2e smoke" "corepack pnpm test-e2e"
Run-Step "source line count" "rg --files -g '!node_modules' -g '!.next' -g '!.next-build' -g '!.next-prod' -g '!dist' -g '!build' -g '!coverage' -g '!test-results' -g '!pnpm-lock.yaml' -g '!*.db' -g '!*.tsbuildinfo' | rg '\.(ts|tsx|py|md|yml|yaml|json|mjs|css|ini|mako|ps1|sh)$' | ForEach-Object { Get-Content -LiteralPath `$_ } | Measure-Object -Line"

$dockerAvailable = $false
docker info *> $null
if ($LASTEXITCODE -eq 0) {
  $dockerAvailable = $true
}
if ($dockerAvailable) {
  Run-Step "docker compose build" "docker compose build"
} else {
  Write-Host "Docker Desktop Linux engine is not reachable; Docker acceptance not executed."
  $results += [PSCustomObject]@{ Name = "docker compose build"; ExitCode = "NOT_RUN_DOCKER_ENGINE_UNAVAILABLE" }
  $failed = $true
}

$results | Format-Table -AutoSize
if ($failed) { exit 1 }
