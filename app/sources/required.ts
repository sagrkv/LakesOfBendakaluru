/** The credit lines the data licences require, in the order the page shows them. */

import type { Source } from "@/lib/lake";
import { purposeOf } from "./catalog";

export type Credit = {
  name: string;
  /** The source key the full entry lives under. */
  anchor: string;
  lines: string[];
  license?: string;
  purpose?: string;
};

const REQUIRED: { name: string; match: RegExp }[] = [
  { name: "ATREE-CSEI", match: /^atree-lakes$/ },
  { name: "OpenStreetMap", match: /^osm-/ },
  { name: "EC Joint Research Centre", match: /^jrc-/ },
  { name: "Copernicus Sentinel-2", match: /^sentinel2-/ },
  { name: "ESA WorldCover", match: /^esa-worldcover/ },
  { name: "Copernicus DEM", match: /^copernicus-dem/ },
  { name: "GBIF", match: /^gbif-/ },
  { name: "Wikidata", match: /^wikidata-/ },
  { name: "Esri World Imagery", match: /^esri-world-imagery$/ },
  { name: "CARTO", match: /^carto-/ },
];

const unique = (values: (string | undefined)[]) => [...new Set(values.filter((v): v is string => Boolean(v)))];

/** "Water area in each year" + "How often..." -> "Water area in each year and how often...". */
function joinPurposes(purposes: string[]): string | undefined {
  if (purposes.length === 0) return undefined;
  return purposes.map((p, i) => (i === 0 ? p : p[0].toLowerCase() + p.slice(1))).join(" and ");
}

export function requiredCredits(sources: Source[]): Credit[] {
  const found = REQUIRED.flatMap(({ name, match }) => {
    const matched = sources.filter((s) => match.test(s.key)).sort((a, b) => a.key.localeCompare(b.key));
    if (matched.length === 0) return [];
    return [
      {
        name,
        anchor: matched[0].key,
        lines: unique(matched.map((s) => s.credit ?? s.title)),
        license: unique(matched.map((s) => s.license)).join("; ") || undefined,
        purpose: joinPurposes(unique(matched.map((s) => purposeOf(s.key)))),
      },
    ];
  });
  return found;
}
