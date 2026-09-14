import type { Metadata } from "next";
import { connection } from "next/server";
import NoOpener from "@/components/home/NoOpener";
import { pickOpener } from "@/components/home/opener";
import Opening from "@/components/home/Opening";
import JsonLd from "@/components/JsonLd";
import SiteFooter from "@/components/SiteFooter";
import { formatCount } from "@/lib/format";
import { getLakes } from "@/lib/lakes";
import { share, SITE_NAME, SITE_URL } from "@/lib/share";

const GITHUB = "https://github.com/sagrkv/LakesOfBendakaluru";

function description(): string {
  const lakes = getLakes();
  const standing = lakes.filter((lake) => lake.status === "exists").length;
  return `${formatCount(standing)} lakes in Bengaluru still exist and ${formatCount(lakes.length - standing)} are gone. Look up any lake to see its size, who looks after it, how clean its water is, how much of it is built over, and every map and report of it since 1800.`;
}

export function generateMetadata(): Metadata {
  return share(SITE_NAME, description(), "/");
}

/** The site, who makes it, and the lake data behind it, for search engines and AI assistants. */
function siteJsonLd(text: string): Record<string, unknown> {
  const maker = { "@type": "Organization", "@id": "https://filtercoffee.dev/#organization", name: "filtercoffee.dev", url: "https://filtercoffee.dev" };
  return {
    "@graph": [
      maker,
      { "@type": "WebSite", "@id": `${SITE_URL}/#website`, url: SITE_URL, name: SITE_NAME, description: text, inLanguage: "en-IN", publisher: { "@id": maker["@id"] } },
      {
        "@type": "Dataset",
        name: "Lakes of Bengaluru",
        description: text,
        url: SITE_URL,
        creator: { "@id": maker["@id"] },
        isAccessibleForFree: true,
        keywords: ["Bengaluru lakes", "Bangalore lakes", "kere", "water quality", "encroachment", "wetlands", "Karnataka"],
        spatialCoverage: {
          "@type": "Place",
          name: "Bengaluru Urban and Bengaluru North districts, Karnataka, India",
          geo: { "@type": "GeoShape", box: "12.66 77.18 13.5 77.97" },
        },
        temporalCoverage: "1799/2026",
        distribution: [
          { "@type": "DataDownload", encodingFormat: "application/json", contentUrl: `${SITE_URL}/data/lakes.json` },
          { "@type": "DataDownload", encodingFormat: "application/geo+json", contentUrl: `${SITE_URL}/data/lakes.geojson` },
        ],
        sameAs: GITHUB,
      },
    ],
  };
}

export default async function HomePage() {
  // A new random lake on every request, never one frozen at build time.
  await connection();
  const opener = pickOpener();

  return (
    <>
      <JsonLd data={siteJsonLd(description())} />
      <main>{opener ? <Opening opener={opener} /> : <NoOpener />}</main>
      <SiteFooter />
    </>
  );
}
