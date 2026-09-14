import { WATER_CLASS } from "@/lib/format";
import type { LakeRecord } from "@/lib/lake";
import { SITE_NAME, SITE_URL } from "@/lib/share";
import { bestAcres } from "./Title";
import { percent } from "./words";

type Fact = { name: string; value: string | number; unitText?: string };

/**
 * The lake as a schema.org LakeBodyOfWater, so search engines and AI assistants can quote its facts:
 * its names, where it is, its size and state, and the encyclopedia entries about the same lake.
 */
export function lakeJsonLd(lake: LakeRecord, name: string, description: string): Record<string, unknown> {
  const url = `${SITE_URL}/lake/${lake.id}`;
  const point = lake.location?.point;
  const place = lake.location?.ward?.name ? `${lake.location.ward.name} ward` : lake.location?.village;
  const size = bestAcres(lake);
  const tested = lake.waterQuality?.latest?.find((reading) => reading.class)?.class;
  const built = lake.location?.hasOutline ? lake.nature?.builtInsideOutlinePct : undefined;
  const custodian = lake.responsibility?.custodian;

  const facts: Fact[] = [
    ...(size ? [{ name: size.label, value: Math.round(size.acres * 10) / 10, unitText: "acres" }] : []),
    ...(lake.water?.valley ? [{ name: "Valley", value: lake.water.valley }] : []),
    ...(custodian ? [{ name: "Looked after by", value: custodian.name }] : []),
    ...(tested ? [{ name: "Water quality class", value: `${tested}: ${WATER_CLASS[tested].short}` }] : []),
    ...(built === undefined ? [] : [{ name: "Built over inside its outline, 2021", value: percent(built) }]),
    ...(lake.status === "exists" ? [] : [{ name: "Status", value: lake.status === "converted" ? "Converted" : "Disappeared" }]),
    ...(lake.history?.goneBy ? [{ name: "Gone by", value: lake.history.goneBy }] : []),
  ];
  const wikipedia = lake.links?.wikipedia;
  const sameAs = [
    lake.links?.wikidata ? `https://www.wikidata.org/wiki/${lake.links.wikidata}` : undefined,
    wikipedia?.en?.url,
    wikipedia?.kn?.url,
  ].filter((link): link is string => Boolean(link));
  const alternateName = [lake.nameKannada, ...(lake.namesOther ?? [])].filter((other): other is string => Boolean(other));

  return {
    "@type": "LakeBodyOfWater",
    "@id": url,
    url,
    name,
    ...(alternateName.length ? { alternateName } : {}),
    description,
    ...(point ? { geo: { "@type": "GeoCoordinates", latitude: point[1], longitude: point[0] } } : {}),
    containedInPlace: {
      "@type": "Place",
      name: place ? `${place}, Bengaluru` : "Bengaluru",
      address: { "@type": "PostalAddress", addressLocality: "Bengaluru", addressRegion: "Karnataka", addressCountry: "IN" },
    },
    additionalProperty: facts.map((fact) => ({ "@type": "PropertyValue", ...fact })),
    ...(sameAs.length ? { sameAs } : {}),
    subjectOf: { "@type": "WebPage", url, isPartOf: { "@type": "WebSite", name: SITE_NAME, url: SITE_URL } },
  };
}
