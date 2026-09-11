// @vitest-environment jsdom
import { cleanup, render } from "@testing-library/react";
import type { EChartsOption } from "echarts";
import { afterEach, describe, expect, it, vi } from "vitest";

const captured = vi.hoisted(() => ({
  option: undefined as EChartsOption | undefined,
}));
vi.mock("next/dynamic", () => ({
  default:
    () =>
    ({ option }: { option: EChartsOption }) => {
      captured.option = option;
      return null;
    },
}));

import { LineChart } from "../components/ui";

afterEach(cleanup);

describe("compact line chart axes", () => {
  it("retains overlap protection when LineChart overrides the shared axes", () => {
    render(<LineChart rows={[]} keys={[]} label="NAV" />);
    expect(captured.option?.xAxis).toMatchObject({
      axisLabel: { fontSize: 10, hideOverlap: true },
    });
    expect(captured.option?.yAxis).toMatchObject({
      axisLabel: { fontSize: 10, hideOverlap: true },
    });
  });

  it("distinguishes fractional percentage ticks instead of rounding all to 2%", () => {
    render(<LineChart rows={[]} keys={[]} label="Volatility" percent />);
    const axis = captured.option?.yAxis;
    if (
      !axis ||
      Array.isArray(axis) ||
      axis.type !== "value" ||
      !axis.axisLabel ||
      !("formatter" in axis.axisLabel) ||
      typeof axis.axisLabel.formatter !== "function"
    ) {
      throw new Error("A percentage axis formatter is required");
    }
    const format = axis.axisLabel.formatter;
    expect(format(0.019, 0)).toBe("1.90%");
    expect(format(0.0195, 1)).toBe("1.95%");
    expect(format(0.02, 2)).toBe("2.00%");
    expect(format(-0.002, 3)).toBe("-0.20%");
    expect(format(0, 4)).toBe("0.00%");
  });
});
