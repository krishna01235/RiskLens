/** @type {import('next').NextConfig} */
const nextConfig = {
  // Required for the Docker multi-stage build: produces a self-contained
  // server.js in .next/standalone that doesn't need the full node_modules.
  output: "standalone",
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
