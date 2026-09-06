# Terminal Shell

Entry: apps/terminal-web/app/[[...slug]]/page.tsx. Shell and routing live in components/shell.tsx and components/pages.tsx.

The shell occupies 100dvh. The function rail, workspace and inspector scroll independently. react-resizable-panels controls the workspace/inspector divider; dimensions are persisted. Below desktop widths the inspector is treated as an overlay and mobile uses monitoring layouts.

Header: brand, active security chips, command entry, workspace switcher, PAPER and DEMO badges, alerts, account control and SGT clock. Quote context comes from persisted quotes, never an invented market-open state. Tabs retain route, security and page parameters. The bottom bar reports measured API latency, actual DB/Redis results and persisted on-demand worker state.

The terminal uses /backend/* as a same-origin proxy. KNK_API_URL defaults to http://127.0.0.1:8000; Compose points it to http://api:8000. Cookies and downloads traverse the same origin. Public web retains its existing API client configuration.

Unknown routes show the function directory/unavailable state rather than silently falling back to Overview. Global security drives new functions, while existing security tabs preserve their security.

Limitations: no detached windows or arbitrary panel docking; workspace storage is single-administrator/shared rather than multi-tenant. Broker/FRED footer labels remain conservative demo/offline summaries, with detailed connection/probe state in Connections and Health.
