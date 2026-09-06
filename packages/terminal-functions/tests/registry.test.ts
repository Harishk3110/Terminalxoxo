import { expect, test } from "vitest";
import {
  findTerminalFunctions,
  functionRoute,
  terminalFunctions,
} from "../src/index";

test("canonical directory has unique mnemonics and honest status fields", () => {
  expect(terminalFunctions.length).toBeGreaterThanOrEqual(110);
  expect(new Set(terminalFunctions.map((f) => f.mnemonic)).size).toBe(
    terminalFunctions.length,
  );
  for (const code of [
    "NAV",
    "PNL",
    "TRADES",
    "RISKMON",
    "QMON",
    "EQUITY",
    "KOYFIN",
    "DATADROP",
    "THESIS",
    "FILINGS",
    "GEX",
  ])
    expect(terminalFunctions.some((f) => f.mnemonic === code)).toBe(true);
  for (const fn of terminalFunctions) {
    expect(fn.route.startsWith("/")).toBe(true);
    expect([
      "available",
      "demo_available",
      "provider_required",
      "in_development",
    ]).toContain(fn.implementationStatus);
  }
});
test("mnemonics, aliases and security routes resolve", () => {
  expect(findTerminalFunctions("BT").map((f) => f.mnemonic)).toContain(
    "BACKTEST",
  );
  expect(
    functionRoute(terminalFunctions.find((f) => f.mnemonic === "FIN")!, "MSFT"),
  ).toBe("/financials/MSFT");
});
