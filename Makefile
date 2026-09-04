.PHONY: bootstrap dev stop test test-unit test-integration test-e2e lint format typecheck migrate seed reset-demo backfill backup restore verify-backup security-check build health broker-agent-build

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
	pnpm backup

restore:
	pnpm restore

verify-backup:
	python infrastructure/scripts/verify_backup.py

security-check:
	pnpm security-check

build:
	pnpm build

health:
	pnpm health

broker-agent-build:
	pnpm broker-agent-build
