"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import { functionRoute } from "@knk/terminal-functions";
import Fuse from "fuse.js";
import {
  Panel as ResizePanel,
  PanelGroup,
  PanelResizeHandle,
} from "react-resizable-panels";
import {
  Bell,
  ChevronDown,
  Copy,
  Download,
  FilePlus2,
  FolderCog,
  Menu,
  PanelRight,
  Plus,
  Search,
  Settings2,
  Star,
  Trash2,
  UserRound,
  X,
} from "lucide-react";
import { TerminalContext } from "./context";
import type {
  Bootstrap,
  Configuration,
  Health,
  Quote,
  Run,
  Tab,
  TerminalFunction,
  Workspace,
} from "./types";
import {
  Badge,
  Empty,
  Field,
  IconButton,
  download,
  money,
  number,
  pct,
  timestamp,
  tone,
} from "./ui";
import { PageRouter } from "./pages";
import { AuthPage } from "./system-pages";
import { safeConfig } from "./workspace";

const emptyConfig: Configuration = {
  tabs: [],
  securities: ["AAPL"],
  rail: true,
  inspector: true,
};
const routeTitle = (route: string, bootstrap: Bootstrap) =>
  bootstrap.functions.find((f) => f.route === route)?.mnemonic ??
  (route.startsWith("/backtests/")
    ? "BACKTEST"
    : route.split("/")[1]?.toUpperCase() || "HOME");

export default function TerminalShell({ route }: { route: string }) {
  const boot = useQuery({
    queryKey: ["bootstrap"],
    queryFn: ({ signal }) =>
      knkApi.get<Bootstrap>("/api/v1/terminal/bootstrap", signal),
    staleTime: 60_000,
  });
  const health = useQuery({
    queryKey: ["terminal-health"],
    queryFn: async ({ signal }) => {
      const start = performance.now();
      const result = await knkApi.get<Health>(
        "/api/v1/terminal/health",
        signal,
      );
      return { ...result, latency: Math.round(performance.now() - start) };
    },
    refetchInterval: 20_000,
  });
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState("");
  const [config, setConfig] = useState<Configuration>(emptyConfig);
  const [loaded, setLoaded] = useState(false);
  const [palette, setPalette] = useState(false);
  const [workspaceModal, setWorkspaceModal] = useState(false);
  const [workspaceName, setWorkspaceName] = useState("");
  const [saveError, setSaveError] = useState("");
  const [clock, setClock] = useState("");
  const [dragTab, setDragTab] = useState("");
  const initialRoute = useRef(route);
  const importRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const compact = window.matchMedia("(max-width: 1279px)");
    const closeInspector = () => {
      if (compact.matches)
        setConfig((current) =>
          current.inspector ? { ...current, inspector: false } : current,
        );
    };
    compact.addEventListener("change", closeInspector);
    return () => compact.removeEventListener("change", closeInspector);
  }, []);
  useEffect(() => {
    if (!boot.data || loaded) return;
    const data = boot.data;
    setWorkspaces(data.workspaces);
    let saved: { workspaceId: string; configuration: Configuration } | null =
      null;
    try {
      saved = JSON.parse(localStorage.getItem("knk-terminal-v2") ?? "null");
    } catch {}
    const ws =
      data.workspaces.find((w) => w.id === saved?.workspaceId) ??
      data.workspaces[0];
    let conf = safeConfig(
      saved && ws.id === saved.workspaceId
        ? saved.configuration
        : ws.configuration,
    );
    {
      const match = conf.tabs.find((t) => t.route === initialRoute.current);
      const tab = match ?? {
        id: crypto.randomUUID(),
        title: routeTitle(initialRoute.current, data),
        route: initialRoute.current,
        security: data.quotes.find(
          (q) => q.symbol === initialRoute.current.split("/")[2],
        )?.symbol,
      };
      conf = {
        ...conf,
        tabs: match ? conf.tabs : [...conf.tabs.slice(-19), tab],
        activeTab: tab.id,
        inspectRunId: ["/stress-tests", "/backtests"].some((p) =>
          initialRoute.current.startsWith(p),
        )
          ? conf.inspectRunId
          : undefined,
      };
    }
    setWorkspaceId(ws.id);
    if (window.innerWidth < 1280) conf = { ...conf, inspector: false };
    setConfig(conf);
    setLoaded(true);
  }, [boot.data, loaded]);
  useEffect(() => {
    const tick = () =>
      setClock(
        new Date().toLocaleTimeString("en-SG", {
          timeZone: "Asia/Singapore",
          hour12: false,
        }),
      );
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);
  useEffect(() => {
    if (!loaded || !workspaceId) return;
    localStorage.setItem(
      "knk-terminal-v2",
      JSON.stringify({ workspaceId, configuration: config }),
    );
    const timer = setTimeout(() => {
      const workspace = workspaces.find((w) => w.id === workspaceId);
      if (workspace)
        knkApi
          .post(`/api/v1/workspaces/${workspaceId}`, {
            name: workspace.name,
            configuration: config,
          })
          .then(() => setSaveError(""))
          .catch((e: Error) => setSaveError(e.message));
    }, 700);
    return () => clearTimeout(timer);
  }, [config, loaded, workspaceId, workspaces]);
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      const input =
        event.target instanceof HTMLElement &&
        ["INPUT", "TEXTAREA", "SELECT"].includes(event.target.tagName);
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPalette((v) => !v);
      } else if (event.key === "/" && !input) {
        event.preventDefault();
        setPalette(true);
      } else if (event.key === "Escape") {
        setPalette(false);
        setWorkspaceModal(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);
  const activeTab =
    config.tabs.find((t) => t.id === config.activeTab) ?? config.tabs[0];
  const security = activeTab?.security ?? config.securities[0] ?? "AAPL";
  const open = useCallback(
    (path: string, title: string, newTab = false, symbol?: string) => {
      setConfig((c) => {
        const found = newTab ? undefined : c.tabs.find((t) => t.route === path);
        const tab = found ?? {
          id: crypto.randomUUID(),
          title,
          route: path,
          security: symbol,
        };
        return {
          ...c,
          tabs: found ? c.tabs : [...c.tabs.slice(-18), tab],
          activeTab: tab.id,
          recents: [
            title,
            ...(c.recents ?? []).filter((t) => t !== title),
          ].slice(0, 12),
          inspectRunId: undefined,
          ...(symbol
            ? {
                securities: [
                  symbol,
                  ...c.securities.filter((s) => s !== symbol),
                ].slice(0, 4),
              }
            : {}),
        };
      });
      window.history.pushState(null, "", path);
    },
    [],
  );
  useEffect(() => {
    const listener = () => {
      const path = window.location.pathname;
      setConfig((c) => {
        const tab = c.tabs.find((t) => t.route === path);
        return tab ? { ...c, activeTab: tab.id } : c;
      });
    };
    window.addEventListener("popstate", listener);
    return () => window.removeEventListener("popstate", listener);
  }, []);
  const selectSecurity = (symbol: string) =>
    setConfig((c) => ({
      ...c,
      tabs: c.tabs.map((t) =>
        t.id === activeTab?.id && t.security
          ? {
              ...t,
              security: symbol,
              route: t.route.replace(/\/[^/]+$/, `/${symbol}`),
              title: `${symbol} ${t.title.split(" ").pop()}`,
            }
          : t,
      ),
      securities: [symbol, ...c.securities.filter((s) => s !== symbol)].slice(
        0,
        4,
      ),
    }));
  if (boot.error?.message.includes("Authentication required"))
    return (
      <div className="main-workspace" style={{ height: "100dvh" }}>
        <AuthPage />
      </div>
    );
  if (boot.error)
    return (
      <Empty
        title="Terminal connection failed"
        detail={(boot.error as Error).message}
      >
        <button onClick={() => boot.refetch()}>Retry API connection</button>
      </Empty>
    );
  if (!boot.data || !loaded || !activeTab)
    return (
      <div className="loading-state" style={{ height: "100dvh" }}>
        Connecting to KnK Capital Terminal
      </div>
    );
  const data = boot.data;
  const quote = data.quotes.find((q) => q.symbol === security);
  const selected = workspaces.find((w) => w.id === workspaceId);
  function switchWorkspace(id: string) {
    setWorkspaces((list) =>
      list.map((w) =>
        w.id === workspaceId ? { ...w, configuration: config } : w,
      ),
    );
    const workspace = workspaces.find((w) => w.id === id);
    if (workspace) {
      const conf = safeConfig(workspace.configuration);
      setConfig(conf);
      setWorkspaceId(id);
      window.history.pushState(
        null,
        "",
        conf.tabs.find((t) => t.id === conf.activeTab)?.route ??
          conf.tabs[0]?.route ??
          "/overview",
      );
    }
  }
  async function workspaceAction(
    action: "create" | "duplicate" | "rename" | "delete",
  ) {
    try {
      if (action === "delete") {
        await knkApi.post(`/api/v1/workspaces/${workspaceId}/delete`);
        const next = workspaces.filter((w) => w.id !== workspaceId);
        setWorkspaces(next);
        setWorkspaceId(next[0].id);
        setConfig(safeConfig(next[0].configuration));
      } else if (action === "rename") {
        const result = await knkApi.post<Workspace>(
          `/api/v1/workspaces/${workspaceId}`,
          { name: workspaceName, configuration: config },
        );
        setWorkspaces((list) =>
          list.map((w) => (w.id === result.id ? result : w)),
        );
      } else {
        const result = await knkApi.post<Workspace>("/api/v1/workspaces", {
          name: workspaceName || `${selected?.name} copy`,
          configuration:
            action === "duplicate"
              ? config
              : {
                  ...emptyConfig,
                  tabs: [
                    {
                      id: crypto.randomUUID(),
                      route: "/overview",
                      title: "HOME",
                    },
                  ],
                },
        });
        setWorkspaces((list) => [
          ...list,
          { ...result, configuration: safeConfig(result.configuration) },
        ]);
        setWorkspaceId(result.id);
        setConfig(safeConfig(result.configuration));
      }
      setWorkspaceModal(false);
    } catch (error) {
      setSaveError((error as Error).message);
    }
  }
  const groupOrder = [
    "markets",
    "portfolio",
    "equities",
    "macro",
    "quant",
    "research",
    "data",
    "reports",
    "tradingview",
    "system",
    "options",
    "fixed-income",
    "fx",
    "crypto",
    "ai",
  ];
  const renderFunction = (fn: TerminalFunction) => {
    const path = functionRoute(fn, security);
    const starred = config.favourites?.includes(fn.mnemonic);
    return (
      <div
        key={fn.mnemonic}
        className={`function-row ${activeTab.route === path ? "selected" : ""}`}
      >
        <button
          className="nav-open"
          title={`${fn.name} / ${fn.implementationStatus.replaceAll("_", " ")}`}
          aria-label={`${fn.mnemonic} ${fn.name}`}
          onClick={() =>
            open(
              path,
              fn.requiresSecurity ? `${security} ${fn.mnemonic}` : fn.mnemonic,
              false,
              fn.requiresSecurity ? security : undefined,
            )
          }
        >
          <span className="mnemonic">{fn.mnemonic}</span>
          <span className="nav-name">{fn.name}</span>
        </button>
        <IconButton
          label={`${starred ? "Unfavourite" : "Favourite"} ${fn.mnemonic}`}
          className={`nav-star ${starred ? "saved amber" : ""}`}
          onClick={() =>
            setConfig((c) => ({
              ...c,
              favourites: starred
                ? c.favourites?.filter((x) => x !== fn.mnemonic)
                : [...(c.favourites ?? []), fn.mnemonic],
            }))
          }
        >
          <Star size={10} />
        </IconButton>
      </div>
    );
  };
  return (
    <TerminalContext.Provider
      value={{
        bootstrap: data,
        config,
        setConfig,
        activeTab,
        security,
        open,
        selectSecurity,
        command: () => setPalette(true),
      }}
    >
      <div className="terminal-shell" data-testid="terminal-shell">
        <header className="global-header">
          <IconButton
            label="Toggle function navigation"
            onClick={() => setConfig((c) => ({ ...c, rail: !c.rail }))}
          >
            <Menu size={15} />
          </IconButton>
          <div className="wordmark">
            <span>KnK</span>
            <b className="brand-capital">CAPITAL</b>
          </div>
          <div className="header-security">
            {config.securities.map((symbol) => (
              <button
                key={symbol}
                className="security-chip"
                onClick={() => selectSecurity(symbol)}
              >
                {symbol}
              </button>
            ))}
          </div>
          <button
            className="command-launch"
            aria-label="Search securities and functions"
            onClick={() => setPalette(true)}
          >
            <Search size={13} />
            <span>Search security or function...</span>
            <kbd>Ctrl K</kbd>
          </button>
          <div className="header-controls">
            <select
              className="workspace-select"
              aria-label="Workspace"
              value={workspaceId}
              onChange={(e) => switchWorkspace(e.target.value)}
            >
              {workspaces.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </select>
            <IconButton
              label="Manage workspaces"
              className="workspace-settings"
              onClick={() => {
                setWorkspaceName(selected?.name ?? "");
                setWorkspaceModal(true);
              }}
            >
              <FolderCog size={14} />
            </IconButton>
            <Badge>PAPER</Badge>
            <Badge>
              {data.quotes.every((q) => q.market_state === "DEMO")
                ? "DEMO DATA"
                : "MIXED SOURCES"}
            </Badge>
            <span className="header-broker muted mono">
              IBKR{" "}
              {health.data?.items.find((x) => x.service === "IBKR paper agent")
                ?.state ?? "UNKNOWN"}
            </span>
            <IconButton label="Alerts" onClick={() => open("/alerts", "ALERT")}>
              <Bell size={14} />
            </IconButton>
            <span className="header-clock mono">{clock} SGT</span>
            <IconButton
              label="Account and login"
              onClick={() => open("/settings/security", "SECURITY")}
            >
              <UserRound size={14} />
            </IconButton>
          </div>
        </header>
        <div className="quote-strip" data-testid="security-context">
          {quote ? (
            <>
              <strong>{quote.symbol}</strong>
              <span className="quote-name">{quote.name}</span>
              <span className="quote-price">{number(quote.price)}</span>
              <span className={tone(quote.change)}>
                {quote.change > 0 ? "+" : ""}
                {number(quote.change)} / {pct(quote.change_pct)}
              </span>
              <span className="secondary">{quote.exchange}</span>
              <span className="muted">{quote.currency}</span>
              <Badge>{quote.market_state}</Badge>
              <div className="quote-meta">
                <span className="source-name">{quote.source}</span>
                <time>As of {timestamp(quote.as_of)} SGT</time>
              </div>
            </>
          ) : (
            <span>No security selected</span>
          )}
        </div>
        <nav className="desk-strip" aria-label="Operating desks">
          {[
            ["PORTFOLIO", "/overview"],
            ["EQUITY", "/equity"],
            ["QUANT", "/quant-dashboard"],
            ["OPTIONS", "/options"],
            ["RISK & TRADE", "/risk-trade-monitor"],
            ["RESEARCH", "/research"],
            ["DATA", "/data-drop"],
            ["SYSTEM", "/system-health"],
          ].map(([label, route]) => (
            <button
              key={label}
              className={activeTab.route === route ? "active" : ""}
              onClick={() => open(route, label)}
            >
              {label}
            </button>
          ))}
        </nav>
        <div className="tab-strip" data-testid="terminal-tabs">
          <div
            className="tabs-scroll"
            role="tablist"
            aria-label="Terminal tabs"
          >
            {config.tabs.map((tab) => (
              <div
                key={tab.id}
                className={`terminal-tab ${tab.id === activeTab.id ? "active" : ""}`}
                draggable
                onDragStart={() => setDragTab(tab.id)}
                onDragOver={(e) => e.preventDefault()}
                onDrop={() =>
                  setConfig((c) => {
                    const tabs = [...c.tabs];
                    const from = tabs.findIndex((t) => t.id === dragTab),
                      to = tabs.findIndex((t) => t.id === tab.id);
                    if (from >= 0 && to >= 0)
                      tabs.splice(to, 0, tabs.splice(from, 1)[0]);
                    return { ...c, tabs };
                  })
                }
              >
                <button
                  role="tab"
                  aria-selected={tab.id === activeTab.id}
                  onClick={() => {
                    setConfig((c) => ({
                      ...c,
                      activeTab: tab.id,
                      inspectRunId: undefined,
                    }));
                    window.history.pushState(null, "", tab.route);
                  }}
                >
                  {tab.dirty ? "* " : ""}
                  {tab.title}
                </button>
                {config.tabs.length > 1 && (
                  <IconButton
                    label={`Close ${tab.title}`}
                    onClick={() =>
                      setConfig((c) => {
                        const tabs = c.tabs.filter((t) => t.id !== tab.id);
                        const next =
                          tab.id === activeTab.id
                            ? tabs[tabs.length - 1]
                            : activeTab;
                        window.history.pushState(null, "", next.route);
                        return { ...c, tabs, activeTab: next.id };
                      })
                    }
                  >
                    <X size={10} />
                  </IconButton>
                )}
              </div>
            ))}
          </div>
          <IconButton label="New terminal tab" onClick={() => setPalette(true)}>
            <Plus size={13} />
          </IconButton>
          <IconButton
            label="Toggle inspector"
            onClick={() =>
              setConfig((c) => ({ ...c, inspector: !c.inspector }))
            }
          >
            <PanelRight size={14} />
          </IconButton>
        </div>
        <div className="workspace-area">
          <aside
            className={`function-rail ${config.rail ? "" : "collapsed"}`}
            data-testid="function-rail"
          >
            <div className="rail-top">
              Functions
              <span className="spacer" />
              <button
                className="icon-button"
                title="Function directory"
                aria-label="Function directory"
                onClick={() => open("/functions", "FUNC")}
              >
                <Search size={12} />
              </button>
            </div>
            <nav className="rail-scroll" aria-label="Functions">
              {Boolean(config.favourites?.length) && (
                <section className="nav-group">
                  <div className="nav-group-title">Favourites</div>
                  {data.functions
                    .filter((f) => config.favourites?.includes(f.mnemonic))
                    .map(renderFunction)}
                </section>
              )}
              {groupOrder.map((category) => (
                <section className="nav-group" key={category}>
                  <button
                    className="nav-group-title"
                    onClick={() =>
                      setConfig((c) => ({
                        ...c,
                        hiddenGroups: (
                          c.hiddenGroups ?? [
                            "equities",
                            "options",
                            "research",
                            "reports",
                            "fixed-income",
                            "fx",
                            "crypto",
                            "ai",
                          ]
                        ).includes(category)
                          ? (
                              c.hiddenGroups ?? [
                                "equities",
                                "options",
                                "research",
                                "reports",
                                "fixed-income",
                                "fx",
                                "crypto",
                                "ai",
                              ]
                            ).filter((g) => g !== category)
                          : [
                              ...(c.hiddenGroups ?? [
                                "equities",
                                "options",
                                "research",
                                "reports",
                                "fixed-income",
                                "fx",
                                "crypto",
                                "ai",
                              ]),
                              category,
                            ],
                      }))
                    }
                  >
                    {category.replace("-", " ")}
                    <ChevronDown size={10} />
                  </button>
                  {!(
                    config.hiddenGroups ?? [
                      "equities",
                      "options",
                      "research",
                      "reports",
                      "fixed-income",
                      "fx",
                      "crypto",
                      "ai",
                    ]
                  ).includes(category) &&
                    data.functions
                      .filter((f) => f.category === category)
                      .map(renderFunction)}
                </section>
              ))}
            </nav>
          </aside>
          <PanelGroup
            direction="horizontal"
            onLayout={(sizes) => {
              if (sizes.length === 2)
                setConfig((c) =>
                  c.sizes?.every((v, i) => Math.abs(v - sizes[i]) < 0.5)
                    ? c
                    : { ...c, sizes },
                );
            }}
          >
            <ResizePanel defaultSize={config.sizes?.[0] ?? 78} minSize={48}>
              <main className="main-workspace" id="main-workspace">
                <div className="mobile-notice">MONITORING</div>
                {saveError && (
                  <div className="warning-note" role="alert">
                    Workspace saved locally; server sync failed: {saveError}
                  </div>
                )}
                <PageRouter route={activeTab.route} />
              </main>
            </ResizePanel>
            {config.inspector && (
              <>
                <PanelResizeHandle className="resize-handle" />
                <ResizePanel
                  className="inspector-panel"
                  defaultSize={config.sizes?.[1] ?? 22}
                  minSize={17}
                  maxSize={34}
                >
                  <Inspector quote={quote} />
                </ResizePanel>
              </>
            )}
          </PanelGroup>
        </div>
        <footer className="status-bar" data-testid="status-bar">
          <button
            className={health.error ? "negative" : "positive"}
            onClick={() => open("/system-health", "HEALTH")}
          >
            API{" "}
            {health.data
              ? `${health.data.latency}ms`
              : health.error
                ? "OFFLINE"
                : "CHECKING"}
          </button>
          <span className={health.data ? "positive" : "warning"}>
            DB {health.data ? "OK" : "UNKNOWN"}
          </span>
          <span
            className={
              health.data?.items.find((x) => x.service === "Redis")?.state ===
              "HEALTHY"
                ? "positive"
                : "warning"
            }
          >
            REDIS{" "}
            {health.data?.items.find((x) => x.service === "Redis")?.state ??
              "UNKNOWN"}
          </span>
          <span className="optional-status secondary">
            QUANT{" "}
            {health.data?.items.find((x) => x.service === "Analytical workers")
              ?.state ?? "UNKNOWN"}
          </span>
          <span className="optional-status secondary">
            DATA{" "}
            {health.data?.items.find((x) => x.service === "Data worker")
              ?.state ?? "UNKNOWN"}
          </span>
          <span className="optional-status secondary">
            REPORT{" "}
            {health.data?.items.find((x) => x.service === "Report service")
              ?.state ?? "UNKNOWN"}
          </span>
          <button
            className="warning optional-status"
            onClick={() => open("/settings/connections", "CONN")}
          >
            FRED{" "}
            {health.data?.items.find((x) => x.service === "FRED")?.state ??
              "UNKNOWN"}
          </button>
          <button
            className="optional-status secondary"
            onClick={() => open("/data-drop", "DATADROP")}
          >
            AGENT{" "}
            {health.data?.items.find((x) => x.service === "Local data agent")
              ?.state ?? "UNKNOWN"}
          </button>
          <button
            className="optional-status secondary"
            onClick={() => open("/overview", "NAV")}
            title={
              health.data?.items.find((x) => x.service === "Portfolio NAV")
                ?.detail
            }
          >
            NAV AS OF{" "}
            {timestamp(
              health.data?.items.find((x) => x.service === "Portfolio NAV")
                ?.as_of,
            )}{" "}
            /{" "}
            {health.data?.items.find((x) => x.service === "Portfolio NAV")
              ?.state ?? "UNKNOWN"}
          </button>
          <button
            className="warning optional-status"
            onClick={() => open("/broker-monitor", "BROKER")}
          >
            IBKR{" "}
            {health.data?.items.find((x) => x.service === "IBKR paper agent")
              ?.state ?? "UNKNOWN"}
          </button>
          <span className="muted optional-status">
            DATA QUALITY{" "}
            {health.data?.items.find((x) => x.service === "Data freshness")
              ?.state ?? "UNKNOWN"}
          </span>
          <span className="muted optional-status">
            BUILD {health.data?.commit ?? "--"}
          </span>
          <span className="status-environment">
            {health.data?.environment.toUpperCase() ?? "UNKNOWN"} / PAPER / SGD
          </span>
        </footer>
      </div>
      {palette && (
        <CommandPalette
          bootstrap={data}
          security={security}
          onClose={() => setPalette(false)}
          open={open}
          selectSecurity={selectSecurity}
        />
      )}
      {workspaceModal && (
        <div className="modal-backdrop">
          <section
            className="modal"
            role="dialog"
            aria-label="Manage workspaces"
          >
            <header className="modal-title">
              <h2>WORKSPACE / {selected?.name}</h2>
              <IconButton
                label="Close workspace settings"
                onClick={() => setWorkspaceModal(false)}
              >
                <X size={14} />
              </IconButton>
            </header>
            <div className="modal-body">
              <Field label="Workspace name">
                <input
                  value={workspaceName}
                  onChange={(e) => setWorkspaceName(e.target.value)}
                />
              </Field>
              <div className="control-row">
                <button onClick={() => workspaceAction("create")}>
                  <Plus size={12} />
                  Create
                </button>
                <button onClick={() => workspaceAction("rename")}>
                  Rename
                </button>
                <button onClick={() => workspaceAction("duplicate")}>
                  <Copy size={12} />
                  Duplicate
                </button>
                <button
                  disabled={workspaces.length < 2}
                  onClick={() => workspaceAction("delete")}
                >
                  <Trash2 size={12} />
                  Delete
                </button>
              </div>
              <div className="control-row">
                <button
                  onClick={() =>
                    setConfig((c) => ({
                      ...c,
                      rail: true,
                      inspector: true,
                      sizes: [78, 22],
                    }))
                  }
                >
                  Reset layout
                </button>
                <button
                  onClick={() =>
                    download(
                      "knk-workspace.json",
                      JSON.stringify(
                        { name: selected?.name, configuration: config },
                        null,
                        2,
                      ),
                      "application/json",
                    )
                  }
                >
                  <Download size={12} />
                  Export
                </button>
                <button onClick={() => importRef.current?.click()}>
                  Import
                </button>
                <input
                  hidden
                  type="file"
                  accept=".json"
                  ref={importRef}
                  onChange={async (e) => {
                    try {
                      const file = e.target.files?.[0];
                      if (file) {
                        const parsed = JSON.parse(await file.text());
                        setConfig(safeConfig(parsed.configuration));
                        setWorkspaceModal(false);
                      }
                    } catch {
                      setSaveError("Invalid workspace JSON");
                    }
                  }}
                />
              </div>
              {saveError && <p role="alert">{saveError}</p>}
            </div>
          </section>
        </div>
      )}
    </TerminalContext.Provider>
  );
}

function CommandPalette({
  bootstrap,
  security,
  onClose,
  open,
  selectSecurity,
}: {
  bootstrap: Bootstrap;
  security: string;
  onClose: () => void;
  open: (
    route: string,
    title: string,
    newTab?: boolean,
    symbol?: string,
  ) => void;
  selectSecurity: (symbol: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const entries = useMemo(
    () => [
      ...bootstrap.quotes.map((q) => ({
        id: q.id,
        code: q.symbol,
        name: q.name,
        category: "Securities",
        keywords: [q.exchange, q.asset_class],
        quote: q,
        fn: undefined as TerminalFunction | undefined,
      })),
      ...bootstrap.functions.map((fn) => ({
        id: fn.mnemonic,
        code: fn.mnemonic,
        name: fn.name,
        category: fn.category,
        keywords: [...fn.keywords, ...fn.aliases],
        fn,
        quote: undefined as Quote | undefined,
      })),
    ],
    [bootstrap],
  );
  const fuse = useMemo(
    () =>
      new Fuse(entries, {
        keys: [
          { name: "code", weight: 3 },
          { name: "name", weight: 2 },
          "keywords",
        ],
        threshold: 0.4,
        ignoreLocation: true,
        includeScore: true,
      }),
    [entries],
  );
  const tokens = query.trim().split(/\s+/);
  const symbol = bootstrap.quotes.find(
    (q) => q.symbol === tokens[0]?.toUpperCase(),
  );
  const term =
    symbol && tokens.length > 1 ? tokens.slice(1).join(" ") : query.trim();
  const results = term
    ? fuse
        .search(term)
        .sort(
          (a, b) =>
            (a.item.code.toLowerCase() === term.toLowerCase() ? -1 : 0) -
              (b.item.code.toLowerCase() === term.toLowerCase() ? -1 : 0) ||
            (a.score ?? 0) - (b.score ?? 0),
        )
        .slice(0, 12)
        .map((r) => r.item)
    : entries.filter((e) =>
        ["HOME", "PORT", "STRESS", "FIN", "BACKTEST", "DROP", "AAPL"].includes(
          e.code,
        ),
      );
  useEffect(() => {
    input.current?.focus();
  }, []);
  useEffect(() => setSelected(0), [query]);
  const choose = (index: number, newTab = false) => {
    const result = results[index];
    if (!result) return;
    if (result.quote) {
      selectSecurity(result.quote.symbol);
      onClose();
      return;
    }
    const fn = result.fn!;
    const active = symbol?.symbol ?? security;
    open(
      functionRoute(fn, active),
      fn.requiresSecurity ? `${active} ${fn.mnemonic}` : fn.mnemonic,
      newTab,
      fn.requiresSecurity ? active : undefined,
    );
    onClose();
  };
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <section
        className="modal command-modal"
        role="dialog"
        aria-label="Command palette"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="command-input">
          <Search size={16} />
          <input
            ref={input}
            role="combobox"
            aria-label="Command"
            aria-expanded="true"
            aria-controls="command-results"
            aria-activedescendant={`command-result-${selected}`}
            placeholder="Security or function..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setSelected((i) => Math.min(results.length - 1, i + 1));
              }
              if (e.key === "ArrowUp") {
                e.preventDefault();
                setSelected((i) => Math.max(0, i - 1));
              }
              if (e.key === "Enter") {
                e.preventDefault();
                choose(selected, e.ctrlKey || e.metaKey);
              }
              if (e.key === "Escape") onClose();
            }}
          />
          <IconButton label="Close command palette" onClick={onClose}>
            <X size={14} />
          </IconButton>
        </div>
        <div id="command-results" className="command-results" role="listbox">
          {results.map((result, index) => (
            <button
              key={result.id}
              id={`command-result-${index}`}
              role="option"
              aria-selected={selected === index}
              className={`command-result ${selected === index ? "selected" : ""}`}
              onMouseEnter={() => setSelected(index)}
              onClick={(e) => choose(index, e.ctrlKey || e.metaKey)}
            >
              <span className="mnemonic">{result.code}</span>
              <span className="result-detail">
                <span>
                  {result.fn?.requiresSecurity
                    ? `${symbol?.symbol ?? security} / `
                    : ""}
                  {result.name}
                </span>
                <small>{result.category.toUpperCase()}</small>
              </span>
              <Badge>
                {result.fn?.implementationStatus.replaceAll("_", " ") ??
                  result.quote?.quality}
              </Badge>
            </button>
          ))}
          {!results.length && <Empty title="No matching records" />}
        </div>
      </section>
    </div>
  );
}

function Inspector({ quote }: { quote?: Quote }) {
  return <InspectorContent quote={quote} />;
}

import { useTerminal } from "./context";
function InspectorContent({ quote }: { quote?: Quote }) {
  const { config, activeTab, setConfig, bootstrap } = useTerminal();
  const runId = config.inspectRunId;
  const run = useQuery({
    queryKey: ["run", runId],
    queryFn: ({ signal }) =>
      knkApi.get<Run>(`/api/v1/terminal/runs/${runId}`, signal),
    enabled: !!runId,
    refetchInterval: (q) =>
      ["QUEUED", "RUNNING"].includes(q.state.data?.status ?? "") ? 700 : false,
  });
  const exportRun = async () => {
    if (!runId) return;
    const report = await knkApi.get<{
      download_url: string;
      report_id?: string;
      id?: string;
    }>(`/api/v1/terminal/runs/${runId}/export`);
    window.open(
      knkApi.downloadUrl(
        report.download_url ??
          `/api/v1/reports/${report.report_id ?? report.id}/download`,
      ),
      "_blank",
      "noopener",
    );
  };
  return (
    <aside className="inspector" data-testid="context-inspector">
      <div className="inspector-title">
        {runId ? "RUN DETAILS" : "CONTEXT / REFERENCE"}
        <span className="spacer" />
        <IconButton
          label="Hide inspector"
          onClick={() => setConfig((c) => ({ ...c, inspector: false }))}
        >
          <X size={12} />
        </IconButton>
      </div>
      <div className="inspector-body">
        {run.data ? (
          <>
            <div className="inspector-section">
              <Badge>{run.data.status}</Badge>
              <h3 style={{ marginTop: 12 }}>{run.data.name}</h3>
              <dl className="detail-list">
                <dt>Run ID</dt>
                <dd>{run.data.id}</dd>
                <dt>Created</dt>
                <dd>{timestamp(run.data.created_at)}</dd>
                <dt>Started</dt>
                <dd>{timestamp(run.data.started_at)}</dd>
                <dt>Completed</dt>
                <dd>{timestamp(run.data.finished_at)}</dd>
                <dt>Portfolio</dt>
                <dd>KnK Reference / SGD</dd>
                <dt>Source</dt>
                <dd>{run.data.result?.source ?? "Persisted inputs"}</dd>
                <dt>Data as of</dt>
                <dd>{timestamp(run.data.result?.as_of)}</dd>
                <dt>Version</dt>
                <dd>{run.data.result?.calculation_version ?? "Pending"}</dd>
              </dl>
            </div>
            {run.data.result && (
              <div className="inspector-section">
                <Badge>{run.data.result.quality}</Badge>
                <Badge>CALCULATED</Badge>
                {run.data.result.warnings.map((w) => (
                  <p className="warning-note" key={w}>
                    {w}
                  </p>
                ))}
                <button onClick={exportRun}>
                  <Download size={12} />
                  Export run XLSX
                </button>
              </div>
            )}
            <div className="inspector-section">
              <h3>Audit history</h3>
              <div className="run-timeline">
                {run.data.history.map((h, i) => (
                  <div key={i}>
                    <span className="action">
                      {h.state} / {timestamp(h.at)}
                    </span>
                    <span>{h.message}</span>
                  </div>
                ))}
              </div>
            </div>
            {run.data.error && <p className="negative">{run.data.error}</p>}
          </>
        ) : (
          <>
            <div className="inspector-section">
              <h3>Active security / Link group 1</h3>
              <strong className="amber mono">{quote?.symbol ?? "--"}</strong>
              <p className="secondary" style={{ marginTop: 6 }}>
                {quote?.name}
              </p>
              <dl className="detail-list" style={{ marginTop: 12 }}>
                <dt>Last</dt>
                <dd>
                  {number(quote?.price)} {quote?.currency}
                </dd>
                <dt>Change</dt>
                <dd className={tone(quote?.change_pct)}>
                  {pct(quote?.change_pct)}
                </dd>
                <dt>Exchange</dt>
                <dd>{quote?.exchange}</dd>
                <dt>Sector</dt>
                <dd>{quote?.sector}</dd>
                <dt>Source</dt>
                <dd>{quote?.source}</dd>
                <dt>Data as of</dt>
                <dd>{timestamp(quote?.as_of)} SGT</dd>
              </dl>
            </div>
            <div className="inspector-section">
              <h3>Data provenance</h3>
              <Badge>{quote?.quality ?? "UNAVAILABLE"}</Badge>
              <p className="warning-note">
                {quote?.quality?.includes("DEMO")
                  ? "Synthetic market records. Not a live quote or an executable price."
                  : "Source-reported observation. The displayed timestamp does not certify live or executable pricing."}
              </p>
            </div>
            <div className="inspector-section">
              <h3>Active function</h3>
              <p className="mono action">{activeTab.title}</p>
              <p className="source-note">{activeTab.route}</p>
            </div>
            <div className="inspector-section">
              <h3>Broker account</h3>
              <Badge>PAPER</Badge>
              <p className="warning-note">
                {bootstrap.broker_state}. No order transmission.
              </p>
            </div>
          </>
        )}
      </div>
    </aside>
  );
}
