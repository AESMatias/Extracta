import type { NextConfig } from "next";

// Production: a static export (plain HTML/JS/CSS in out/) served by Nginx, which also proxies
// /api to Flask. No Node.js server runs on the 2 GB machine.
// Development (`npm run dev`): Next.js serves the pages and forwards /api to the Flask API.
const isDev = process.env.NODE_ENV === "development";
const apiOrigin = process.env.API_ORIGIN ?? "http://localhost:8000";

const config: NextConfig = {
  output: isDev ? undefined : "export",
  images: { unoptimized: true },
  poweredByHeader: false,
  // One build worker: keeps `next build` inside ~1 GB so it fits on a 2 GB server (with swap).
  experimental: { cpus: 1 },
  reactStrictMode: true,
  ...(isDev && {
    async rewrites() {
      return [{ source: "/api/:path*", destination: `${apiOrigin}/api/:path*` }];
    },
  }),
};

export default config;
