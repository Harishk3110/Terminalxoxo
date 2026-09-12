# Tomorrow Deployment

Status: PARTIAL. No hosted URL or authorised cloud deployment is certified.
The requested tomorrow-deploy wrappers are not implemented yet. Do not substitute
a frontend-only upload for the required persistent backend and worker deployment.

Existing intended Vercel project/root/settings are in PRODUCTION_HOSTING_STATUS.md.
Use the existing target only after confirming authorised account access. Do not
create duplicate projects. One frontend only: apps/terminal-web.

## Prerequisites

- All 29 required local release stages pass on a frozen source checkpoint.
- Production database/object backups and isolated restore are verified.
- Administrator provisioning, password/TOTP setup and private session routing pass.
- PostgreSQL SSL, Redis TLS where applicable, private object storage, worker queues,
  health/readiness, CORS, cookie and trusted-proxy configuration are validated.
- Production KNK_API_URL is an authorised HTTPS origin, not loopback/private host.
  No provider secrets use NEXT_PUBLIC variables. No demo production password.

## Order

1. Verify the existing backend target, credentials and rollback image references.
2. Take a verified backup; apply migrations with the existing migration command.
3. Deploy API, data/quant/report workers and persistent services.
4. Verify liveness, readiness, worker heartbeat and private object access.
5. Deploy apps/terminal-web to the existing Vercel project with Node 22.
6. Verify root/private overview routing, anonymous denial and session/API connectivity.
7. Run TOMORROW_SMOKE_TESTS.md and record exact URLs, HTTP results and commit IDs.

The existing PowerShell local release wrapper lists its currently implemented
commands without executing them: `scripts/release-candidate.ps1 --list`.
The runner's update from 27 to 29 stages is still pending. Deployment commands
will be finalised only after inspecting the actual authorised hosting targets;
no fabricated backend hostname or token-based command is supplied here.
