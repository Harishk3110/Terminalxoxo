import { z } from "zod";
import type { Configuration } from "./types";

const tab = z.object({
  id: z.string().min(1),
  title: z.string().min(1).max(100),
  route: z.string().regex(/^\/(?!\/)[A-Za-z0-9/_-]*$/),
  security: z.string().optional(),
  dirty: z.boolean().optional(),
});
const schema = z.object({
  tabs: z.array(tab).max(20).default([]),
  activeTab: z.string().optional(),
  securities: z.array(z.string().min(1).max(20)).max(4).default(["AAPL"]),
  rail: z.boolean().default(true),
  inspector: z.boolean().default(true),
  sizes: z.array(z.number().min(0).max(100)).length(2).optional(),
  favourites: z.array(z.string()).optional(),
  recents: z.array(z.string()).optional(),
  watchlist: z.array(z.string()).optional(),
  hiddenGroups: z.array(z.string()).optional(),
  inspectRunId: z.string().optional(),
  tabStates: z.record(z.record(z.unknown())).optional(),
});

export function safeConfig(value: unknown): Configuration {
  const parsed = schema.safeParse(value);
  const config: Configuration = parsed.success
    ? parsed.data
    : { tabs: [], securities: ["AAPL"], rail: true, inspector: true };
  if (!config.tabs.length)
    config.tabs = [{ id: "home", route: "/overview", title: "HOME" }];
  return config;
}
