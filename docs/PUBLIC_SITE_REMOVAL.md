# Public Site Removal

Recovery tag: pre-terminal-only-cleanup, pushed before deletion.
Tagged commit: 1be9a594252c18729de123173c7d5d3cedeaeec6.

## Removed

Tracked source: all 12 files under apps/public-web, including route, layout,
styles, content, package/configuration files and the second Vercel configuration.
Also removed: packages/publishing/README.md, docs/PUBLISHING.md, shared
publicResearch fixtures and the visitor-only SecurityNotice component.

Visitor routes removed: principles, products and product detail, methodology,
about, contact, disclosures, privacy, legal and visitor research pages.
Private /research remains an authenticated investment workspace.
The /api/v1/public/content endpoint and its unauthenticated exception were removed.
The public research seed was removed. Existing research_notes is a shared private
terminal model, not a disposable visitor model; historical rows are preserved.

Root scripts, workspace membership, Compose, CI, acceptance scripts and hosting
instructions now describe one terminal. The public-web Compose service and
PUBLIC_WEB_ORIGIN environment variable were removed. Port 3000's owned process
was stopped. No public Vercel project is part of active configuration.

Public-content tests were replaced with route-absence assertions. Session tests
cover anonymous rejection even in local demo, logout/revocation and disabled users.
Browser tests cover root redirect, noindex and absent visitor pages.

## Filesystem Limitation

The source deletions succeeded. A separate recursive removal of ignored build and
dependency artifacts under the former app directory was denied by execution policy.
That inert directory may remain on this machine; no alternate deletion was attempted.
It is excluded from workspace membership and is not in the deployable Git tree.
Therefore physical directory absence is not claimed.

No portfolio, database, audit, imported raw file or existing valuation run was
deleted by this cleanup. The only active frontend is apps/terminal-web.
