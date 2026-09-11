import type { MacroDashboardPayload } from "@knk/api-client";
import type { Row } from "./types";

function observationDate(value: unknown): Date | null {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value))
    return null;
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isFinite(date.getTime()) &&
    date.toISOString().slice(0, 10) === value
    ? date
    : null;
}

export function macroRange(rows: Row[], range: string): Row[] {
  const dated = rows.map((row) => ({
    ...row,
    date: row.observation_date ?? row.date,
  }));
  if (range === "MAX") return dated;
  const times = dated
    .map((row) => observationDate(row.date)?.getTime())
    .filter((time): time is number => time !== undefined);
  if (!times.length) return [];
  const latest = new Date(Math.max(...times));
  const cutoff = new Date(latest);
  cutoff.setUTCFullYear(latest.getUTCFullYear() - (range === "1Y" ? 1 : 5));
  if (cutoff.getUTCMonth() !== latest.getUTCMonth()) cutoff.setUTCDate(0);
  return dated.filter((row) => {
    const date = observationDate(row.date);
    return date !== null && date >= cutoff;
  });
}

export function macroProvenance(items: MacroDashboardPayload["items"]) {
  const available = items.filter((item) => item.latest_value !== null);
  const sources = [...new Set(available.map((item) => item.source))];
  const qualities = [...new Set(available.map((item) => item.quality))];
  const dates = available.map((item) =>
    observationDate(item.latest_observation_date),
  );
  return {
    source: sources.join(" / ") || "Source unavailable",
    quality:
      qualities.length === 1
        ? qualities[0]
        : qualities.length
          ? "MIXED SOURCES"
          : "UNAVAILABLE",
    asOf:
      dates.length && dates.every((date) => date !== null)
        ? new Date(Math.min(...dates.map((date) => date!.getTime())))
            .toISOString()
            .slice(0, 10)
        : null,
  };
}
