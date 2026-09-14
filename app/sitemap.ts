import type { MetadataRoute } from "next";
import { getLakes } from "@/lib/lakes";
import { SITE_URL } from "@/lib/share";

/** Every page: the six site pages, then a page for each of the lakes, standing lakes first. */
export default function sitemap(): MetadataRoute.Sitemap {
  const pages: MetadataRoute.Sitemap = ["", "/map", "/timeline", "/once-upon-a-kere", "/missing-lakes", "/sources"].map(
    (path) => ({ url: `${SITE_URL}${path}`, changeFrequency: "weekly", priority: path ? 0.8 : 1 }),
  );
  const lakes = [...getLakes()].sort((a, b) => Number(b.status === "exists") - Number(a.status === "exists"));
  return [
    ...pages,
    ...lakes.map((lake) => ({
      url: `${SITE_URL}/lake/${lake.id}`,
      changeFrequency: "monthly" as const,
      priority: lake.status === "exists" ? 0.7 : 0.5,
    })),
  ];
}
