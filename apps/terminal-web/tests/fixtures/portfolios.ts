import type {
  PortfolioCreationOptions,
  PortfolioRecord,
} from "../../components/ledger/portfolio-create";
import { metadata } from "./accounting";

export const creationOptions: PortfolioCreationOptions = {
  currencies: ["EUR", "SGD", "USD"],
  methods: ["AVERAGE", "FIFO"],
  max_opening_date: "2026-09-06",
  date_boundary: "UTC",
  maximum_capital: "1E+12",
  capital_decimal_places: 8,
  benchmarks: [
    { symbol: "AAPL", name: "Apple Inc.", currency: "USD" },
    { symbol: "SPY", name: "SPDR S&P 500", currency: "USD" },
  ],
};

export const mainLedger: PortfolioRecord = {
  ...metadata,
  id: "main-book",
  code: "KNK_MAIN",
  name: "KnK Capital Main Portfolio",
  reference_capital: "70000.00000000",
  is_demo: true,
  is_default: true,
  configuration: { allow_short: true, benchmark: "SPY" },
};

export const researchLedger: PortfolioRecord = {
  ...metadata,
  id: "research-book",
  code: "RESEARCH",
  name: "Research allocation",
  base_currency: "USD",
  reference_capital: "1000.12345678",
  is_demo: false,
  is_default: false,
  configuration: {
    allow_short: false,
    benchmark: "SPY",
    opening_date: "2026-09-06",
  },
};
