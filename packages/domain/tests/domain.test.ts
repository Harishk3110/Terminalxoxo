import { describe, expect, it } from "vitest";
import {
  calculateMaxDrawdown,
  calculateResidualNotional,
  calculateSimpleReturn,
  roundHedgeUnits
} from "../src/index";

describe("domain calculations", () => {
  it("calculates simple return", () => {
    expect(calculateSimpleReturn(100, 112)).toBeCloseTo(0.12);
  });

  it("calculates max drawdown from an equity curve", () => {
    expect(calculateMaxDrawdown([100, 120, 90, 110])).toBeCloseTo(-0.25);
  });

  it("rounds hedge units and residual notional", () => {
    const units = roundHedgeUnits(250000, 50, 5628.5);
    expect(units).toBe(1);
    expect(calculateResidualNotional(250000, units, 50, 5628.5)).toBeCloseTo(-31425);
  });
});
