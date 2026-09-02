import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
      {
        source: "/video_feed",
        destination: "http://localhost:8000/video_feed",
      },
      {
        source: "/raw_feed",
        destination: "http://localhost:8000/raw_feed",
      },
      {
        source: "/seed_demo_data",
        destination: "http://localhost:8000/seed_demo_data",
      },
    ];
  },
};

export default nextConfig;
