$ErrorActionPreference = "Stop"

Write-Host "Preparing KnK Capital Terminal dependencies..."
corepack prepare pnpm@9.15.4 --activate
corepack pnpm install
python -m pip install -r services/api/requirements.txt

$dockerAvailable = $false
docker info *> $null
if ($LASTEXITCODE -eq 0) {
  $dockerAvailable = $true
}
if ($dockerAvailable) {
  Write-Host "Docker engine is running."
} else {
  Write-Host "Docker Desktop is installed but the Linux engine is not reachable. Start Docker Desktop, wait until it says running, then rerun docker compose up --build."
}
