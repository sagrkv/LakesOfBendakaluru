import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The opening screen picks a lake per request and reads its file from disk, so ship the data with it.
  outputFileTracingIncludes: {
    "/": ["./public/data/*.json", "./public/data/lake/*.json"],
  },
};

export default nextConfig;
