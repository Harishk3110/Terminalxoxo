/** @type {import('next').NextConfig} */
const nextConfig = {
  distDir: process.env.KNK_NEXT_DIST_DIR || ".next-prod",
  env: { NEXT_PUBLIC_API_BASE_URL: "/backend" },
  transpilePackages: ["@knk/design-system", "@knk/domain", "@knk/api-client", "@knk/search", "@knk/terminal-functions"],
  poweredByHeader: false
};

export default nextConfig;
