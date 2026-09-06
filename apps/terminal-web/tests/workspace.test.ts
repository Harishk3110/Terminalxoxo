import { describe, expect, it } from "vitest";
import { safeConfig } from "../components/workspace";

describe("workspace state", () => {
  it("restores tab state and panel sizes", () => {
    const config = {
      tabs: [{ id: "test", route: "/stress-tests", title: "STRESS" }],
      sizes: [75, 25],
      tabStates: { test: { shock: -20 } },
    };
    expect(safeConfig(config).tabStates).toEqual(config.tabStates);
    expect(safeConfig(config).sizes).toEqual([75, 25]);
  });
  it("rejects malformed imports and external routes", () => {
    for (const invalid of [
      null,
      { tabs: "oops" },
      { tabs: [{ id: "x", title: "BAD", route: "//other.example" }] },
    ]) {
      expect(safeConfig(invalid).tabs[0].route).toBe("/overview");
    }
  });
  it("keeps an empty imported workspace usable", () => {
    expect(safeConfig({ tabs: [] }).tabs).toHaveLength(1);
  });
  it("migrates saved alpha payloads to references without discarding their controls", () => {
    const state = {
      "alpha-result": {
        id: "saved-analysis",
        results: { NET: { rolling: "x".repeat(200001) } },
      },
      "alpha-config": { model: "CAPM", confidence: ".95" },
    };
    const migrated = safeConfig({ tabStates: { alpha: state } });
    expect(migrated.tabStates?.alpha).toEqual({
      "alpha-run": "saved-analysis",
      "alpha-config": state["alpha-config"],
    });
    expect(JSON.stringify(migrated).length).toBeLessThan(200000);
    expect(state["alpha-result"].id).toBe("saved-analysis");
  });
});
