import type { Metadata } from "next";

export const SITE_NAME = "Lakes of Bendakaluru";
export const SITE_HOST = "lakesofbendakaluru.filtercoffee.dev";
export const SITE_URL = `https://${SITE_HOST}`;
export const SITE_IMAGE_ALT = "Lakes of Bendakaluru: the largest lake of each valley in Bengaluru, cut out of coloured paper.";

/**
 * The page title and description, repeated for link previews and cards so they always say the same thing.
 * The preview image is the site's, unless the route draws its own with an opengraph-image file: pass `ownImage`,
 * since an image named here would replace the route's own.
 * `path` sets the canonical address, so search engines count one page once.
 */
export function share(title: string, description: string, path?: string, ownImage = false): Metadata {
  const images = ownImage ? {} : { images: [{ url: "/opengraph-image", width: 1200, height: 630, alt: SITE_IMAGE_ALT }] };
  return {
    title: { absolute: title },
    description,
    ...(path === undefined ? {} : { alternates: { canonical: path } }),
    openGraph: {
      title,
      description,
      siteName: SITE_NAME,
      type: "website",
      locale: "en_IN",
      ...(path === undefined ? {} : { url: path }),
      ...images,
    },
    twitter: { card: "summary_large_image", title, description, ...images },
  };
}
