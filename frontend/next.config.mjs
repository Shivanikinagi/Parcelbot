/** @type {import('next').NextConfig} */
const API_BASE = process.env.BACKEND_ORIGIN || "http://127.0.0.1:8000";

const nextConfig = {
  reactStrictMode: true,
  // Proxy API calls to the FastAPI backend so the browser talks to one origin
  // (avoids CORS in dev and mirrors a reverse-proxy production setup).
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_BASE}/api/:path*` }];
  },
};

export default nextConfig;
