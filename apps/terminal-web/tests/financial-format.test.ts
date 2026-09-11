import { describe, expect, it } from "vitest";
import Decimal from "decimal.js";
import {
  money,
  number,
  pct,
  significant,
  tone,
} from "../components/financial-format";

describe("decimal-preserving financial display", () => {
  it.each([
    ["0.000275346", "0.000275346"],
    ["-0.000275346", "-0.000275346"],
    ["1.234565", "1.23456"],
    ["1.234575", "1.23458"],
    ["1e-10000", "1.00000e-10000"],
    ["-1e-10000", "-1.00000e-10000"],
    ["1e100000", "1.00000e+100000"],
    ["0", "0"],
    ["-0", "0"],
    [null, "--"],
    [undefined, "--"],
    [Infinity, "--"],
    [true, "--"],
    [[], "--"],
    ["", "--"],
  ])("retains statistical significance for %s", (value, expected) => {
    expect(significant(value)).toBe(expected);
  });

  it.each([0, -1, 1.5, 13, Infinity, NaN])(
    "rejects invalid significant precision %s",
    (digits) => {
      expect(significant(1.23, digits)).toBe("--");
    },
  );

  it.each([
    ["9999999999999999.12345678", 8, "9,999,999,999,999,999.12345678"],
    ["-9999999999999999.12345678", 8, "-9,999,999,999,999,999.12345678"],
    ["9007199254740993", 0, "9,007,199,254,740,993"],
    ["0.123456785", 8, "0.12345678"],
    ["0.123456795", 8, "0.12345680"],
    ["1.005", 2, "1.00"],
    ["1.015", 2, "1.02"],
    ["-1.005", 2, "-1.00"],
    ["-1.015", 2, "-1.02"],
    ["999.995", 2, "1,000.00"],
    ["2.5", 0, "2"],
    ["3.5", 0, "4"],
    ["0E+23", 8, "0.00000000"],
    ["1.23456789e8", 8, "123,456,789.00000000"],
    ["  +.1250  ", 3, "0.125"],
    ["-0.001", 2, "0.00"],
    ["-0", 2, "0.00"],
    ["1e-10000", 2, "0.00"],
  ])(
    "formats %s to %i places using half-even rounding",
    (value, places, expected) => {
      expect(number(value, places)).toBe(expected);
    },
  );

  it.each([
    null,
    undefined,
    "",
    " ",
    "NaN",
    "Infinity",
    "-Infinity",
    NaN,
    Infinity,
    true,
    false,
    {},
    [],
    "12,000",
    "SGD 12",
    "0x10",
    "0b10",
    "1_000",
    "12 apples",
    "1e",
    "1e999999999999999999999999",
    "9".repeat(257),
  ])("retains invalid or absent %j as unavailable", (value) => {
    expect(number(value)).toBe("--");
    expect(pct(value)).toBe("--");
    expect(tone(value)).toBe("");
    expect(money(value)).toBe("S$--");
  });

  it.each([-1, 1.5, 13, NaN, Infinity])(
    "rejects unsupported display precision %s without throwing",
    (places) => {
      expect(number("12.34", places)).toBe("--");
    },
  );

  it("preserves existing numeric chart inputs while keeping exact integer inputs", () => {
    expect(number(1234.5)).toBe("1,234.50");
    expect(number(9007199254740993n, 0)).toBe("9,007,199,254,740,993");
    expect(number("0.1234567890125", 12)).toBe("0.123456789012");
  });

  it("formats ratios without an intervening binary conversion and keeps unavailable percentages bare", () => {
    expect(pct("0.10005")).toBe("+10.00%");
    expect(pct("0.10015")).toBe("+10.02%");
    expect(pct("-0.10015")).toBe("-10.02%");
    expect(pct("123456789012345.12345")).toBe("+12,345,678,901,234,512.34%");
    expect(pct("0")).toBe("0.00%");
    expect(pct("-0")).toBe("0.00%");
    expect(pct(" ")).toBe("--");
  });

  it("uses bounded scientific output for extreme magnitudes", () => {
    expect(number("1e100000", 8)).toBe("1.00000000e+100000");
    expect(number("-1e100000", 2)).toBe("-1.00e+100000");
    expect(pct("1e100000")).toBe("+1.00e+100002%");
    expect(number("1e36", 0)).toBe(
      "1,000,000,000,000,000,000,000,000,000,000,000,000",
    );
    expect(number("1e37", 0)).toBe("1e+37");
    expect(pct("1e9000000000000000")).toBe("--");
  });

  it("keeps monetary prefix and sign conventions without changing the source value", () => {
    const value = "-12345678901234.125";
    expect(money(value)).toBe("S$-12,345,678,901,234.12");
    expect(value).toBe("-12345678901234.125");
    expect(tone("1e-1000")).toBe("positive");
    expect(tone("-1e-1000")).toBe("negative");
    expect(tone(-0)).toBe("");
  });

  it("does not invoke arbitrary object coercion", () => {
    const object = {
      toString() {
        throw new Error("Unsafe coercion");
      },
    };
    expect(number(object)).toBe("--");
    expect(pct(object)).toBe("--");
  });

  it("isolates display precision from unrelated decimal.js configuration changes", () => {
    const before = { precision: Decimal.precision, rounding: Decimal.rounding };
    try {
      Decimal.set({ precision: 3, rounding: Decimal.ROUND_UP });
      expect(number("12345678901234.125")).toBe("12,345,678,901,234.12");
      expect(pct("0.10005")).toBe("+10.00%");
    } finally {
      Decimal.set(before);
    }
  });
});
