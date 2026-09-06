import type { Config } from "tailwindcss";

const config: Config = {
  content: { relative: true, files: ["./app/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}", "../../packages/design-system/src/**/*.{ts,tsx}"] },
  theme: {
    extend: {
      colors: {
        ink: "#111827",
        copper: "#b45309",
        harbor: "#0e7490"
      }
    }
  },
  plugins: []
};

export default config;
