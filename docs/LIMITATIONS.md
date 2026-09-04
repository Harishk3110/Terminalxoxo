# Limitations

Current limitations as of 2026-09-05:

- Full Docker Compose build/startup/health is not validated because Docker Desktop's Linux engine is not running locally.
- FRED live mode is implemented but unverified with a real key in this environment.
- Backend coverage is 81% overall and does not yet meet every directive target.
- Backend lint/typecheck gates such as Ruff and mypy are not configured.
- CSV and JSON uploads are implemented; XLSX and Parquet parsing are not yet active in workers.
- Report generation is functional for the required workbook families, but report orchestration is not yet fully worker-driven.
- The backtest engine supports the deterministic moving-average crossover path; broader strategy families are persisted but not fully executable.
- Grafana dashboard JSON provisioning is not complete.
- Session revocation, CSRF middleware, and login throttling enforcement require more hardening.
- No live broker execution exists by design.
