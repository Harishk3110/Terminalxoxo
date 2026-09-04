/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ["@knk/design-system", "@knk/domain", "@knk/search", "@knk/terminal-functions"],
  poweredByHeader: false
};

export default nextConfig;
