/** @type {import('next').NextConfig} */
const nextConfig = {
  distDir: process.env.KNK_PUBLIC_DIST_DIR || ".next-prod",
  transpilePackages: ["@knk/design-system", "@knk/domain"],
  poweredByHeader: false
};

export default nextConfig;
