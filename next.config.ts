import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The opening screen picks a lake per request and reads its file from disk, so ship the data with it.
  // Lake preview images are drawn on first request too, from the lake's file and the serif.
  outputFileTracingIncludes: {
    "/": ["./public/data/*.json", "./public/data/lake/*.json"],
    "/lake/[id]/opengraph-image": ["./public/data/*.json", "./public/data/lake/*.json", "./assets/fonts/*.ttf"],
  },
  redirects() {
    return [{ source: "/forgotten", destination: "/once-upon-a-kere", permanent: true }];
  },
};

export default nextConfig;
