# Deployment

Local deployment uses Docker Compose. Production deployment should isolate public-web, terminal-web, API, workers, report engine, PostgreSQL, Redis, object storage, monitoring, and broker-agent pairing endpoints.

Public web can be deployed separately from the terminal. Public routes must not share private server-side queries.
