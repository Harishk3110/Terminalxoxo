import { publicResearch } from "@knk/domain";

export const publicRoutes = [
  "/",
  "/principles",
  "/products",
  "/products/terminal",
  "/research",
  "/research/demo-quality-growth-framework",
  "/research/demo-risk-first-portfolio-construction",
  "/methodology",
  "/about",
  "/contact",
  "/legal",
  "/privacy",
  "/disclosures"
];

export const products = [
  {
    slug: "terminal",
    name: "KnK Capital Terminal",
    summary: "Private research, portfolio, risk, and reporting operating system for KnK Capital."
  },
  {
    slug: "quant-engine",
    name: "KnK Quant Engine",
    summary: "Demo-mode factor research, backtesting, model validation, and portfolio construction."
  },
  {
    slug: "research-studio",
    name: "KnK Research Studio",
    summary: "Private thesis workspace with sanitized public publishing controls."
  }
];

export { publicResearch };
