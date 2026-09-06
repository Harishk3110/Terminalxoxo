import type { Config } from "tailwindcss";

const config: Config = {
  content: {
    relative: true,
    files: [
      "./app/**/*.{ts,tsx}",
      "./components/**/*.{ts,tsx}",
      "./lib/**/*.{ts,tsx}",
      "../../packages/design-system/src/**/*.{ts,tsx}",
    ],
  },
  theme: {
    extend: {
      colors: {
        terminal: "#101820",
        panel: "#17212b",
        accent: "#0e7490",
        copper: "#b45309",
      },
    },
  },
  plugins: [],
};

export default config;
