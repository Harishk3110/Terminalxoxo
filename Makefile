.PHONY: bootstrap dev stop test test-unit test-integration test-e2e lint format typecheck migrate seed reset-demo backfill backup backup-sqlite restore verify-backup verify-backup-sqlite restore-test security-check build health broker-agent-build

PYTHON ?= $(firstword $(wildcard .venv-rc/Scripts/python.exe .venv-rc/bin/python) python)
RELEASE_ARGS ?=
BACKUP_ARGS ?=
BACKUP_ARCHIVE ?=
BACKUP_SHA256 ?=

bootstrap:
	corepack prepare pnpm@9.15.4 --activate
	pnpm install

dev:
	pnpm dev

stop:
	docker compose down

test:
	pnpm test

test-unit:
	pnpm test-unit

test-integration:
	pnpm test-integration

test-e2e:
	pnpm test-e2e

lint:
	pnpm lint

format:
	pnpm format

typecheck:
	pnpm typecheck

migrate:
	pnpm migrate

seed:
	pnpm seed

reset-demo:
	pnpm reset-demo

backfill:
	pnpm backfill

backup:
	$(PYTHON) -m infrastructure.scripts.managed_backup backup $(BACKUP_ARGS)

backup-sqlite:
	pnpm backup

restore:
	pnpm restore

verify-backup:
	$(PYTHON) -m infrastructure.scripts.managed_backup verify --archive "$(BACKUP_ARCHIVE)"

verify-backup-sqlite:
	$(PYTHON) infrastructure/scripts/verify_backup.py "$(BACKUP_ARCHIVE)"

restore-test:
	$(PYTHON) -m infrastructure.scripts.managed_backup restore-test --archive "$(BACKUP_ARCHIVE)" --sha256 "$(BACKUP_SHA256)" $(BACKUP_ARGS)

security-check:
	pnpm security-check

build:
	pnpm build

health:
	pnpm health

broker-agent-build:
	pnpm broker-agent-build

.PHONY: release-candidate
release-candidate:
	$(PYTHON) scripts/release_candidate.py $(RELEASE_ARGS)
