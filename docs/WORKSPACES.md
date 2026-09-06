# Workspaces

Workspace metadata is in workspaces; version-2 layout JSON is in workspace_states. Endpoints:
- GET/POST /api/v1/workspaces
- POST /api/v1/workspaces/{id}
- POST /api/v1/workspaces/{id}/delete

Nine layouts are seeded only when there are no workspaces. Local state is cached under knk-terminal-v2. Changes are debounced to the server; server failures leave a visible local-only sync warning. Existing workspaces can be switched, created, duplicated, renamed, deleted (except the last), imported/exported as JSON, and reset to default panel sizes.

Persisted configuration includes tabs/order/active tab, selected securities, favorites, recent functions, collapsed groups, inspector visibility and sizes, watchlist and page-specific parameters. Tabs store security context separately. Zod validates imported configurations and rejects external routes and malformed structures.

Per-tab state includes scenario assumptions, selected runs, macro series/range, portfolio view, backtest parameters, research draft and manual hedge review state. Table saved views use separate localStorage keys.

Limits: no server revision merge/conflict resolution, per-user ownership, cross-device live synchronization or unsaved-close confirmation. Reset resets panel layout, not analytical data.
