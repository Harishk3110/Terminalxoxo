/** @type {import('next').NextConfig} */
const nextConfig = {
  distDir: ".next-prod",
  transpilePackages: ["@knk/design-system", "@knk/domain"],
  poweredByHeader: false
};

export default nextConfig;
