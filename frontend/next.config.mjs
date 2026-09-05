/** @type {import('next').NextConfig} */
const nextConfig = {
  // NOTE: output: "standalone" is intentionally removed here.
  // It is only needed for Docker deployments. Vercel is incompatible with
  // standalone mode and requires the default .next output layout.
  // To restore Docker support, re-add: output: "standalone"
  typescript: {
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
