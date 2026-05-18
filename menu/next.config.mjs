const apiProxyTarget = (process.env.NEXT_PUBLIC_API_PROXY_TARGET || process.env.NEXT_PUBLIC_API_URL || "https://backend.neuros.my")
  .trim()
  .replace(/\/+$/, "");

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api-proxy/:path*",
        destination: `${apiProxyTarget}/:path*`,
      },
    ];
  },
  images: {
    remotePatterns: [{ protocol: "https", hostname: "**" }],
  },
};

export default nextConfig;
