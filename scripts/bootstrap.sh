#!/usr/bin/env sh
set -eu

echo "Preparing KnK Capital Terminal dependencies..."
corepack prepare pnpm@9.15.4 --activate
corepack pnpm install
python -m pip install -r services/api/requirements.txt

if docker info >/dev/null 2>&1; then
  echo "Docker engine is running."
else
  echo "Docker Desktop or the Docker daemon is not reachable. Start it, then rerun docker compose up --build."
fi
