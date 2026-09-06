import { describe, expect, it } from "vitest";
import { safeConfig } from "../components/workspace";

describe("workspace state", () => {
  it("restores tab state and panel sizes", () => {
    const config = { tabs: [{id:"test",route:"/stress-tests",title:"STRESS"}], sizes:[75,25], tabStates:{test:{shock:-20}} };
    expect(safeConfig(config).tabStates).toEqual(config.tabStates);
    expect(safeConfig(config).sizes).toEqual([75,25]);
  });
  it("rejects malformed imports and external routes", () => {
    for (const invalid of [null, {tabs:"oops"}, {tabs:[{id:"x",title:"BAD",route:"//other.example"}]}]) {
      expect(safeConfig(invalid).tabs[0].route).toBe("/overview");
    }
  });
  it("keeps an empty imported workspace usable", () => {
    expect(safeConfig({tabs:[]}).tabs).toHaveLength(1);
  });
});
