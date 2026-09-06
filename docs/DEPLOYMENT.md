# Deployment

Local deployment uses Docker Compose. Production isolates terminal-web, API, workers, report engine, PostgreSQL, Redis, object storage, monitoring and broker-agent pairing endpoints.

There is one private frontend. See PRODUCTION_HOSTING_STATUS.md for Vercel settings and backend prerequisites. Authentication and noindex are mandatory.
