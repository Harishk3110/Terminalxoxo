# Repository Structure

```text
apps/public-web        Public KnK Capital website
apps/terminal-web      Private terminal shell
services/api           FastAPI backend
services/worker-data   Data ingestion worker
services/worker-quant  Quant worker
services/report-engine Report generation service
services/broker-agent  Local read-only broker agent
packages/*             Shared domain, UI, search, and analytical packages
infrastructure/*       Docker, deployment, backup, and scripts
monitoring/*           Prometheus and Grafana configuration
tests/*                Unit, integration, security, contract, and e2e tests
docs/*                 Product, operations, and methodology documentation
```
