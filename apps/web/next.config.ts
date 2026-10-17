import type { NextConfig } from "next";

const config: NextConfig = {
  reactStrictMode: true,
  devIndicators: false,
  // Match the backend's inference deadline instead of cutting off /ask at 30s.
  experimental: { proxyTimeout: 900_000 },
  async rewrites() {
    const backend = (process.env.BRAINBOB_API_URL ?? "http://127.0.0.1:3001").replace(/\/$/, "");
    return [{ source: "/api/brainbob/:path*", destination: `${backend}/:path*` }];
  },
};

export default config;
