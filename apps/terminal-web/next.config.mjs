/** @type {import('next').NextConfig} */
const nextConfig = {
  distDir: ".next-prod",
  transpilePackages: ["@knk/design-system", "@knk/domain", "@knk/api-client", "@knk/search", "@knk/terminal-functions"],
  poweredByHeader: false
};

export default nextConfig;
