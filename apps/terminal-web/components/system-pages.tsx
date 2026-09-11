"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import { Check, LogOut, RefreshCw } from "lucide-react";
import { records, useTerminal } from "./context";
import { Badge, DataTable, Empty, Field, Panel, timestamp } from "./ui";
import { PageTitle, useApi } from "./core-pages";
import type { Health, ProviderPayload, Row } from "./types";
import { AccountSecurity } from "./account-security";

export function HealthPage() {
  const query = useApi<Health>(
    "terminal-health-page",
    "/api/v1/terminal/health",
  );
  return (
    <>
      <PageTitle code="HEALTH" title="System Health / Observed State">
        <span className="secondary mono">
          BUILD {query.data?.commit ?? "--"}
        </span>
        <button onClick={() => query.refetch()}>
          <RefreshCw size={12} />
          Probe services
        </button>
      </PageTitle>
      <Panel
        className="page-grid"
        title="Service probes and heartbeat coverage"
        source="Current probe results"
        asOf={query.data?.as_of}
        quality="OBSERVED"
        loading={query.isLoading}
        error={query.error}
        onRefresh={() => query.refetch()}
      >
        <DataTable
          id="service-health"
          rows={records(query.data?.items ?? [])}
          columns={[
            { key: "service", label: "Service", size: 175 },
            {
              key: "state",
              label: "State",
              size: 145,
              format: (v) => <Badge>{String(v)}</Badge>,
            },
            {
              key: "latency_ms",
              label: "Latency (ms)",
              numeric: true,
              size: 110,
            },
            {
              key: "as_of",
              label: "Checked / SGT",
              size: 170,
              format: (v) => timestamp(v),
            },
            { key: "detail", label: "Evidence", size: 410 },
          ]}
        />
      </Panel>
    </>
  );
}

export function ConnectionsPage() {
  const query = useApi<ProviderPayload>("providers", "/api/v1/providers");
  const [message, setMessage] = useState("");
  const mutation = useMutation({
    mutationFn: () => knkApi.post<Row>("/api/v1/providers/fred/test"),
    onSuccess: (r) => {
      setMessage(
        String(
          r.status ??
            r.state ??
            r.connection_state ??
            "Connection test returned",
        ),
      );
      query.refetch();
    },
    onError: (e) => setMessage(e.message),
  });
  const backfill = useMutation({
    mutationFn: () =>
      knkApi.post<Row>("/api/v1/macro/backfills", {
        series_ids: ["FEDFUNDS", "DGS2", "DGS10"],
        observation_start: "2016-01-01",
      }),
    onSuccess: (r) =>
      setMessage(String(r.status ?? r.state ?? "Backfill submitted")),
    onError: (e) => setMessage(e.message),
  });
  return (
    <>
      <PageTitle code="CONN" title="Connections / Data Providers">
        <button disabled={mutation.isPending} onClick={() => mutation.mutate()}>
          Test FRED connection
        </button>
        <button disabled={backfill.isPending} onClick={() => backfill.mutate()}>
          Run FRED backfill
        </button>
      </PageTitle>
      {message && (
        <p className="warning-note" role="status">
          {message}
        </p>
      )}
      <Panel
        className="page-grid"
        title="Provider configuration and capability state"
        source="Server-side provider registry"
        quality="OBSERVED"
        error={query.error}
        loading={query.isLoading}
      >
        <DataTable
          id="provider-connections"
          rows={records(query.data?.items ?? [])}
          columns={[
            { key: "name", label: "Provider", size: 175 },
            {
              key: "connection_state",
              label: "State",
              size: 155,
              format: (v) => <Badge>{String(v)}</Badge>,
            },
            {
              key: "configured",
              label: "Configured",
              size: 90,
              format: (v) => (v ? "YES" : "NO"),
            },
            {
              key: "enabled",
              label: "Enabled",
              size: 80,
              format: (v) => (v ? "YES" : "NO"),
            },
            {
              key: "capabilities",
              label: "Capabilities",
              size: 290,
              format: (v) => (v as string[]).join(", "),
            },
            {
              key: "last_success",
              label: "Last success",
              size: 160,
              format: (v) => timestamp(v as string),
            },
            { key: "last_error", label: "Last error", size: 280 },
          ]}
        />
      </Panel>
      <p className="source-note">
        Credentials are configured on the server. Demo market data remains
        labelled independently when FRED connects.
      </p>
    </>
  );
}

export function AlertsPage() {
  const query = useApi<{ items: Row[] }>("alerts", "/api/v1/alerts");
  const [error, setError] = useState("");
  return (
    <>
      <PageTitle code="ALERT" title="Alerts / Review Queue" />
      <Panel
        className="page-grid"
        title="Active and acknowledged alerts"
        source="KnK alert records"
        quality="DEMO DATA"
        error={query.error}
        loading={query.isLoading}
      >
        <DataTable
          id="alerts"
          rows={query.data?.items ?? []}
          columns={[
            {
              key: "severity",
              label: "Severity",
              size: 100,
              format: (v) => <Badge>{String(v)}</Badge>,
            },
            { key: "title", label: "Alert", size: 210 },
            { key: "message", label: "Detail", size: 350 },
            { key: "state", label: "State", size: 110 },
            {
              key: "id",
              label: "Action",
              size: 125,
              format: (_, row) => (
                <button
                  disabled={row.state === "RESOLVED"}
                  onClick={() =>
                    knkApi
                      .post(`/api/v1/alerts/${row.id}/acknowledge`)
                      .then(() => query.refetch())
                      .catch((e) => setError(e.message))
                  }
                >
                  <Check size={11} />
                  Acknowledge
                </button>
              ),
            },
          ]}
        />
        {error && <p role="alert">{error}</p>}
      </Panel>
    </>
  );
}

export function AuthPage() {
  const session = useApi<{
    authenticated: boolean;
    setup_required: boolean;
    email?: string;
    role?: string;
  }>("auth-session", "/api/v1/auth/session");
  const client = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const [useRecovery, setUseRecovery] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function login(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (session.data?.setup_required)
        await knkApi.post("/api/v1/auth/setup", { email, password });
      await knkApi.post("/api/v1/auth/login", {
        email,
        password,
        totp_code: useRecovery ? null : totp || null,
        recovery_code: useRecovery ? totp || null : null,
      });
      setPassword("");
      client.invalidateQueries();
      window.location.assign("/overview");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageTitle code="SECURITY" title="Account / Authentication" />
      <div className="page-grid equal-grid">
        <Panel
          title={
            session.data?.authenticated
              ? "Current session"
              : session.data?.setup_required
                ? "Create administrator"
                : "Sign in"
          }
          source="KnK authentication service"
          quality="PRIVATE"
          error={session.error}
        >
          {session.data?.authenticated ? (
            <div className="modal-body">
              <Badge>AUTHENTICATED</Badge>
              <p>{session.data.email}</p>
              <p>{session.data.role}</p>
              <button
                onClick={() =>
                  knkApi
                    .post("/api/v1/auth/logout")
                    .then(() => {
                      client.clear();
                      window.location.assign("/login");
                    })
                    .catch((reason) => setError(reason.message))
                }
              >
                <LogOut size={12} /> Sign out
              </button>
              <button
                onClick={() =>
                  knkApi
                    .post("/api/v1/auth/logout-all")
                    .then(() => {
                      client.clear();
                      window.location.assign("/login");
                    })
                    .catch((reason) => setError(reason.message))
                }
              >
                <LogOut size={12} /> Sign out all sessions
              </button>
              {error && (
                <p className="error-state" role="alert">
                  {error}
                </p>
              )}
            </div>
          ) : (
            <form onSubmit={login} className="modal-body">
              <Field label="Email">
                <input
                  aria-label="Email"
                  autoComplete="username"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </Field>
              <Field label="Password">
                <input
                  aria-label="Password"
                  autoComplete={
                    session.data?.setup_required
                      ? "new-password"
                      : "current-password"
                  }
                  type="password"
                  required
                  minLength={12}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </Field>
              <label className="security-checkbox">
                <input
                  type="checkbox"
                  checked={useRecovery}
                  onChange={(e) => {
                    setUseRecovery(e.target.checked);
                    setTotp("");
                  }}
                />{" "}
                Use recovery code
              </label>
              <Field
                label={useRecovery ? "Recovery code" : "TOTP code (if enabled)"}
              >
                <input
                  aria-label={useRecovery ? "Recovery code" : "TOTP code"}
                  autoComplete="one-time-code"
                  maxLength={useRecovery ? 128 : 6}
                  value={totp}
                  onChange={(e) => setTotp(e.target.value)}
                />
              </Field>
              <button className="primary-button" disabled={busy} type="submit">
                {busy
                  ? "Signing in..."
                  : session.data?.setup_required
                    ? "Create administrator and sign in"
                    : "Sign in"}
              </button>
              {error && (
                <p className="negative" role="alert">
                  {error}
                </p>
              )}
            </form>
          )}
        </Panel>
        {session.data?.authenticated ? (
          <AccountSecurity />
        ) : (
          <Panel
            title="Environment access"
            source="Server configuration"
            quality="LOCAL DEMO"
          >
            <dl className="detail-list section-pad">
              <dt>Mode</dt>
              <dd>Local demo / paper</dd>
              <dt>Session</dt>
              <dd>HTTP-only cookie / 8 hours</dd>
              <dt>Broker</dt>
              <dd>Manual execution only</dd>
              <dt>Access</dt>
              <dd>Private terminal / sign-in required</dd>
            </dl>
          </Panel>
        )}
      </div>
    </>
  );
}

export function FunctionDirectory({ route }: { route: string }) {
  const { bootstrap, open, security } = useTerminal();
  const fn = bootstrap.functions.find((f) => f.route === route);
  if (route !== "/functions")
    return (
      <>
        <PageTitle
          code={fn?.mnemonic ?? "FUNCTION"}
          title={fn?.name ?? "Unknown function"}
        />
        <Panel
          className="page-grid"
          title="Function availability"
          source="Canonical function registry"
          asOf={bootstrap.as_of}
          quality={fn?.implementationStatus.toUpperCase() ?? "UNAVAILABLE"}
        >
          <Empty
            title={
              fn?.implementationStatus === "provider_required"
                ? "Provider required"
                : "Function is not operational"
            }
            detail={
              fn?.providerRequirements.join(", ") ??
              "This route is not registered."
            }
          >
            <button onClick={() => open("/settings/connections", "CONN")}>
              Connections
            </button>
            <button onClick={() => open("/functions", "FUNC")}>
              Function directory
            </button>
          </Empty>
        </Panel>
      </>
    );
  return (
    <>
      <PageTitle code="FUNC" title="Function Directory / Capability Registry">
        <span className="secondary">
          {bootstrap.functions.length} functions
        </span>
      </PageTitle>
      <Panel
        className="page-grid"
        title="All registered functions"
        source="Canonical function registry"
        asOf={bootstrap.as_of}
        quality="OBSERVED"
      >
        <DataTable
          id="function-directory"
          rows={records(bootstrap.functions)}
          columns={[
            { key: "mnemonic", label: "Function", size: 110 },
            { key: "name", label: "Name", size: 225 },
            { key: "category", label: "Category", size: 120 },
            {
              key: "implementationStatus",
              label: "Availability",
              size: 170,
              format: (v) => <Badge>{String(v).replaceAll("_", " ")}</Badge>,
            },
            {
              key: "requiresSecurity",
              label: "Security",
              size: 90,
              format: (v) => (v ? "REQUIRED" : "GLOBAL"),
            },
            {
              key: "providerRequirements",
              label: "Provider requirements",
              size: 240,
              format: (v) => (v as string[]).join(", "),
            },
          ]}
          onSelect={(row) =>
            open(
              String(row.route).replace("{instrumentId}", security),
              String(row.mnemonic),
              false,
              Boolean(row.requiresSecurity) ? security : undefined,
            )
          }
        />
      </Panel>
    </>
  );
}

export function ReconciliationPage() {
  return (
    <>
      <PageTitle code="RECON" title="Broker / Reference Reconciliation" />
      <Panel
        className="page-grid"
        title="Reconciliation state"
        source="Broker provider configuration"
        quality="PROVIDER REQUIRED"
      >
        <Empty
          title="IBKR paper account is not connected"
          detail="No broker balance or position has been reported. Reference ledger data cannot establish a reconciliation result."
        />
      </Panel>
    </>
  );
}
