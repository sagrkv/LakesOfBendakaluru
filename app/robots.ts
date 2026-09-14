import type { MetadataRoute } from "next";
import { SITE_HOST, SITE_URL } from "@/lib/share";

/** Open to every crawler, search engines and AI assistants alike: the site exists to be found and quoted. */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/" },
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_HOST,
  };
}
