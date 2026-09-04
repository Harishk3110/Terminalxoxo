import { AlertTriangle, CheckCircle2, Database, Lock, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";
import { clsx } from "clsx";

export function ModeBadge({ children, tone = "demo" }: { children: ReactNode; tone?: "demo" | "paper" | "ok" | "warn" }) {
  return (
    <span
      className={clsx(
        "inline-flex h-7 items-center gap-1 rounded border px-2 text-xs font-semibold uppercase tracking-normal",
        tone === "demo" && "border-amber-400/50 bg-amber-100 text-amber-950",
        tone === "paper" && "border-sky-400/50 bg-sky-100 text-sky-950",
        tone === "ok" && "border-emerald-400/50 bg-emerald-100 text-emerald-950",
        tone === "warn" && "border-rose-400/50 bg-rose-100 text-rose-950"
      )}
    >
      {tone === "demo" ? <Database className="h-3.5 w-3.5" /> : null}
      {tone === "paper" ? <ShieldCheck className="h-3.5 w-3.5" /> : null}
      {tone === "ok" ? <CheckCircle2 className="h-3.5 w-3.5" /> : null}
      {tone === "warn" ? <AlertTriangle className="h-3.5 w-3.5" /> : null}
      {children}
    </span>
  );
}

export function DataTraceLine({
  provider,
  dataset,
  timestamp,
  quality
}: {
  provider: string;
  dataset: string;
  timestamp: string;
  quality: string;
}) {
  return (
    <p className="text-xs text-slate-500">
      {quality} | {provider} | {dataset} | {timestamp}
    </p>
  );
}

export function StatBlock({
  label,
  value,
  sublabel,
  tone = "neutral"
}: {
  label: string;
  value: string;
  sublabel?: string;
  tone?: "neutral" | "positive" | "negative";
}) {
  return (
    <section className="rounded-md border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase text-slate-500">{label}</p>
      <p
        className={clsx(
          "mt-2 text-2xl font-semibold tracking-normal",
          tone === "positive" && "text-emerald-700",
          tone === "negative" && "text-rose-700",
          tone === "neutral" && "text-slate-950"
        )}
      >
        {value}
      </p>
      {sublabel ? <p className="mt-1 text-sm text-slate-500">{sublabel}</p> : null}
    </section>
  );
}

export function SecurityNotice() {
  return (
    <section className="rounded-md border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
        <Lock className="h-4 w-4" />
        Public/private separation active
      </div>
      <p className="mt-2 text-sm text-slate-600">
        Public routes use sanitized content only. Private portfolio, broker, research draft, and signal data stay behind authenticated terminal APIs.
      </p>
    </section>
  );
}
