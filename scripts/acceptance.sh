#!/usr/bin/env sh
set -u
failed=0

run_step() {
  name="$1"
  command="$2"
  echo "== $name =="
  sh -c "$command"
  code=$?
  echo "$name exit=$code"
  if [ "$code" -ne 0 ]; then
    failed=1
  fi
  return 0
}

run_step "git status" "git status --short --branch"
run_step "python dependencies" "python -m pip install -r services/api/requirements.txt"
run_step "javascript dependencies" "corepack pnpm install"
run_step "alembic upgrade" "DATABASE_URL=sqlite:///./knk_acceptance.db alembic upgrade head"
run_step "demo seed" "DATABASE_URL=sqlite:///./knk_acceptance.db python services/api/scripts/seed_demo.py --reset"
run_step "backend tests" "python -m pytest services/api/tests"
run_step "frontend typecheck" "corepack pnpm typecheck"
run_step "frontend lint" "corepack pnpm lint"
run_step "frontend tests and security" "corepack pnpm test"
run_step "terminal build" "NEXT_PUBLIC_APP_ENV=test corepack pnpm --filter @knk/terminal-web build"
run_step "e2e smoke" "corepack pnpm test-e2e"
run_step "source line count" "rg --files -g '!node_modules' -g '!.next' -g '!.next-build' -g '!.next-prod' -g '!dist' -g '!build' -g '!coverage' -g '!test-results' -g '!pnpm-lock.yaml' -g '!*.db' -g '!*.tsbuildinfo' | grep -E '\\.(ts|tsx|py|md|yml|yaml|json|mjs|css|ini|mako|ps1|sh)$' | xargs wc -l"

if docker info >/dev/null 2>&1; then
  run_step "docker compose build" "docker compose build"
else
  echo "Docker Desktop or Docker daemon is not reachable; Docker acceptance not executed."
  failed=1
fi

exit "$failed"
