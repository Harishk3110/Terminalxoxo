# Security

## Implemented Controls

- Argon2 password hashing for administrator setup/login.
- TOTP secret generation during setup.
- HTTP-only cookies for setup/session markers.
- CORS allowlist for local public and terminal origins.
- Security headers: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and Content Security Policy.
- Audit logging for administrator setup.
- Provider credentials loaded from environment variables.
- Provider status responses do not return secrets.
- Public content endpoint returns sanitized research notes only.
- Security tests verify public/private API separation.
- Node and Python source guards scan application source for forbidden broker execution method names.
- Secret scan executed for common AWS/OpenAI/GitHub/FRED key patterns.

## Broker Execution Boundary

The repository intentionally has no broker order execution API. The safety guard scans for:

`placeOrder`, `cancelOrder`, `reqGlobalCancel`, `transmitOrder`, `modifyOrder`, `submitOrder`, `executeTrade`, `autoRebalance`, and `autoHedge`.

The UI may display manual recommendations but must not submit, transmit, cancel, or modify broker orders.

## Current Gaps

- Login throttling is recorded through `login_attempts` but no rate-limit middleware is enforced yet.
- CSRF middleware is not fully implemented.
- Session revocation APIs are not yet exposed.
- Dependency scanning is represented by local tests/scans; a dedicated SCA tool is not configured.
- Backend static lint/typecheck gates are not configured yet.
