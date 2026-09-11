import Decimal from "decimal.js";

const DisplayDecimal = Decimal.clone({
  precision: 80,
  rounding: Decimal.ROUND_HALF_EVEN,
});
const integerFormat = new Intl.NumberFormat("en-SG", {
  maximumFractionDigits: 0,
});
const decimalLiteral = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i;
const MAX_INPUT_LENGTH = 256;
const MAX_FIXED_EXPONENT = 36;
const MAX_PLACES = 12;

function parsed(value: unknown): Decimal | null {
  if (
    typeof value !== "string" &&
    typeof value !== "number" &&
    typeof value !== "bigint"
  )
    return null;
  const text = String(value).trim();
  if (!text || text.length > MAX_INPUT_LENGTH || !decimalLiteral.test(text))
    return null;
  try {
    const result = new DisplayDecimal(text);
    return result.isFinite() ? result : null;
  } catch {
    return null;
  }
}

function formatted(value: Decimal, places: number): string {
  if (!Number.isInteger(places) || places < 0 || places > MAX_PLACES)
    return "--";
  if (value.e > MAX_FIXED_EXPONENT) return value.toExponential(places);
  const rounded = value.toDecimalPlaces(places);
  const [integer, fraction] = rounded.abs().toFixed(places).split(".");
  const sign = rounded.isNegative() && !rounded.isZero() ? "-" : "";
  return (
    sign +
    integerFormat.format(BigInt(integer)) +
    (fraction ? "." + fraction : "")
  );
}

export function number(value: unknown, places = 2): string {
  const decimal = parsed(value);
  return decimal === null ? "--" : formatted(decimal, places);
}

export function significant(value: unknown, digits = 6): string {
  const decimal = parsed(value);
  if (
    decimal === null ||
    !Number.isInteger(digits) ||
    digits < 1 ||
    digits > MAX_PLACES
  )
    return "--";
  return decimal.isZero() ? "0" : decimal.toPrecision(digits);
}

export function pct(value: unknown): string {
  const decimal = parsed(value);
  if (decimal === null) return "--";
  const percent = decimal.times(100);
  if (!percent.isFinite()) return "--";
  return (
    (percent.isPositive() && !percent.isZero() ? "+" : "") +
    formatted(percent, 2) +
    "%"
  );
}

export function money(value: unknown): string {
  return "S$" + number(value);
}

export function tone(value: unknown): "positive" | "negative" | "" {
  const decimal = parsed(value);
  if (decimal === null || decimal.isZero()) return "";
  return decimal.isPositive() ? "positive" : "negative";
}
