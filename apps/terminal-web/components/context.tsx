"use client";
import {
  createContext,
  useCallback,
  useContext,
  type Dispatch,
  type SetStateAction,
} from "react";
import { useQuery } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import type {
  Bootstrap,
  Configuration,
  PortfolioData,
  Row,
  Tab,
} from "./types";

export interface TerminalContextValue {
  bootstrap: Bootstrap;
  config: Configuration;
  setConfig: Dispatch<SetStateAction<Configuration>>;
  activeTab: Tab;
  security: string;
  open: (
    route: string,
    title: string,
    newTab?: boolean,
    security?: string,
  ) => void;
  selectSecurity: (symbol: string) => void;
  command: () => void;
}
export const TerminalContext = createContext<TerminalContextValue | null>(null);
export function useTerminal() {
  const value = useContext(TerminalContext);
  if (!value) throw new Error("Terminal context missing");
  return value;
}
export function usePortfolio() {
  return useQuery({
    queryKey: ["terminal-portfolio"],
    queryFn: ({ signal }) =>
      knkApi.get<PortfolioData>("/api/v1/terminal/portfolio", signal),
  });
}
export function useTabState<T>(
  key: string,
  initial: T,
): [T, (value: T) => void] {
  const { config, setConfig, activeTab } = useTerminal();
  const value = config.tabStates?.[activeTab.id]?.[key] as T | undefined;
  const update = useCallback(
    (next: T) =>
      setConfig((c) => ({
        ...c,
        tabStates: {
          ...c.tabStates,
          [activeTab.id]: { ...c.tabStates?.[activeTab.id], [key]: next },
        },
      })),
    [activeTab.id, key, setConfig],
  );
  return [value ?? initial, update];
}
export function records<T extends object>(items: T[]): Row[] {
  return items as unknown as Row[];
}
