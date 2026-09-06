import { fileURLToPath } from "node:url";
/** @type {import('next').NextConfig} */
const nextConfig = {
  distDir: process.env.KNK_PUBLIC_DIST_DIR || ".next",
  outputFileTracingRoot: fileURLToPath(new URL("../../", import.meta.url)),
  transpilePackages: ["@knk/design-system", "@knk/domain"],
  poweredByHeader: false
};

export default nextConfig;
