# Account Security

Implemented in the 2026-09-11 final-build checkpoint. This is not a certification
of the complete production security requirements.

## Authenticated Workflows

Open `/settings/security` after signing in. Enrollment requires the current
password, expires after ten minutes, and enables TOTP only after a valid code.
Eight recovery codes are returned once on confirmation or replacement. Only
Argon2 hashes are retained. The status endpoint never returns authenticator seeds,
recovery-code plaintext or session token hashes.

TOTP uses six digits and 30-second intervals, accepting the adjacent interval for
clock drift. A persisted conditional update consumes each accepted time step once.
Recovery-code consumption is also conditional and atomic. Password-only login is
rejected when TOTP is enabled. Successful recovery login revokes previous sessions.

Authenticator disablement, password changes and recovery-code replacement require
the current password plus TOTP or an unused recovery code when MFA is enabled.
Password changes revoke every session. Enrollment and disablement revoke all but
the current session. Session listing and individual revocation are user-scoped;
another user's session identifier returns 404. Failed proofs count toward the
persisted authentication throttle. Security changes are audited without secrets.

Endpoints under `/api/v1/auth`:

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/security` | MFA state, remaining recovery count, own active sessions |
| POST | `/totp/enroll` | Expiring encrypted enrollment challenge |
| POST | `/totp/confirm` | Confirm challenge and issue recovery codes once |
| POST | `/totp/disable` | Disable MFA after reauthentication |
| POST | `/recovery-codes` | Replace the previous recovery-code set |
| POST | `/password` | Change password and sign out all sessions |
| POST | `/sessions/{id}/revoke` | Revoke an owned session |
| POST | `/login` | Password plus enabled TOTP or recovery code |

## Encryption and Recovery

`AUTH_SECRET` must be a URL-safe base64-encoded 32-byte Fernet key. It is separate
from passwords and recovery codes. Non-local environments fail closed when the key
is absent, invalid or cannot decrypt an enrolled secret.

For local demo only, an absent key creates a persistent key file at
`KNK_AUTH_KEY_FILE` or `~/.knk-capital/auth.key`. Creation is exclusive; an existing
file is reused, never silently rotated. POSIX creation modes are 0700/0600.
Windows deployments must restrict the directory ACL to the service account and
administrators; a POSIX mode alone does not configure Windows ACLs.

The Docker bootstrap generates `AUTH_SECRET` in ignored `.env.compose.local`.
Back up that file securely with the associated database. Local SQLite/object
archive commands do **not** include the external authentication key automatically.
Restore the original key as well as the database; generating a replacement key
does not recover existing enrollments. Never commit keys or unencrypted backups.

Legacy `local-demo:` seeds are accepted only in local-demo mode and are encrypted
after a successful TOTP proof. They must be migrated before production deployment.
Key rotation and a bulk administrative migration/recovery CLI remain outstanding.

The implementation follows [PyOTP's replay-prevention guidance](https://pyauth.github.io/pyotp/)
and uses [Fernet authenticated encryption](https://cryptography.io/en/latest/fernet/).

## Verified Scope and Gaps

Twenty focused API/security tests passed, covering enrollment expiry, replay,
recovery reuse, password changes, key handling and session ownership. Four changed
authentication modules passed scoped strict typing. The new browser workflow passed
enrollment, password-only rejection, recovery login/reuse rejection and disablement,
with inspected 1440px and 390px screenshots. These are not a full penetration test.

Trusted-device registration/expiry/revocation is not implemented. A session is not
silently treated as a trusted device and never bypasses enabled MFA. Production
administrator provisioning, key-rotation operations and broader concurrency,
authorization, session and deployment reviews remain final-build tasks.
