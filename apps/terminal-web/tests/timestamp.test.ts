import { describe, expect, it } from "vitest";
import { timestamp } from "../components/ui";

describe("observed timestamps", () => {
  it.each([
    undefined,
    null,
    "",
    " ",
    "null",
    "undefined",
    "bad-date",
    0,
    false,
    {},
  ])("does not manufacture a timestamp for %j", (value) =>
    expect(timestamp(value)).toBe("Not observed"),
  );

  it("renders recorded UTC and explicit offset timestamps in Singapore time", () => {
    const utc = timestamp("2026-01-02T00:15:00Z");
    expect(utc).toContain("02 Jan 2026");
    expect(utc).toContain("08:15");
    expect(timestamp("2026-01-02T08:15:00+08:00")).toBe(utc);
    expect(timestamp("2026-01-02T00:15:00")).toBe(utc);
  });

  it("does not call arbitrary object string conversions", () => {
    expect(
      timestamp({
        toString: () => {
          throw new Error("Unexpected conversion");
        },
      }),
    ).toBe("Not observed");
  });
});
