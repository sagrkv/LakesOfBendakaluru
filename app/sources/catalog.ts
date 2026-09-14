/** Reading sources.json for the sources page: what each source is for, its date, and publisher groups. */

import type { Source } from "@/lib/lake";
import { formatMonth } from "@/lib/format";

/** What a source is used for, from its key. See docs/lake-data-model.md. */
const PURPOSES: [RegExp, string][] = [
  [/^atree-lakes$/, "Lake outlines"],
  [/^bbmp-custody$/, "Who looks after each lake and its extent on land records"],
  [/^bbmp-lms$/, "Lake locations and BBMP lake pages"],
  [/^cascade-/, "Which lake drains into which"],
  [/^citizenmatters-/, "Residents' groups"],
  [/^copernicus-dem/, "Valleys and elevation"],
  [/^(dmg-|lakes-2015|jakkur-|nwmp-)/, "Older water tests"],
  [/^empri-/, "Lost lakes, encroachment and condition in 2018"],
  [/^esa-worldcover/, "Land around each lake"],
  [/^gbif-/, "Birds and other species"],
  [/^inaturalist-/, "Wildlife sightings"],
  [/^jrc-gsw-.*yearly/, "Water area in each year"],
  [/^jrc-gsw-/, "How often each lake held water"],
  [/^kgis-/, "Outlines for lakes missing from the ATREE map"],
  [/^kspcb-/, "Water quality"],
  [/^ktcda-/, "Who looks after each lake"],
  [/^landrecords-/, "Official lake maps"],
  [/^osm-/, "Outlines, Kannada names and nearby treatment plants"],
  [/^sentinel2-/, "Open water and floating weed today"],
  [/^(ams|soi)-/, "Whether a lake was on old survey maps"],
  [/^wards-/, "Ward and city corporation"],
  [/^wbc-/, "Water Bodies Census entry"],
  [/^wikidata-/, "Kannada names and links"],
  [/^wikipedia-/, "Lake summaries"],
];

export function purposeOf(key: string): string | undefined {
  return PURPOSES.find(([pattern]) => pattern.test(key))?.[1];
}

export function notStated(value: string | undefined): boolean {
  return !value || value.toLowerCase().startsWith("not stated");
}

/** "2025-12-28" -> "28 Dec 2025", "2023-07" -> "Jul 2023", anything else as written. */
export function formatAsOf(asOf: string | undefined): string | undefined {
  if (!asOf || notStated(asOf)) return undefined;
  const day = asOf.match(/^(\d{4}-\d{2})-(\d{2})$/);
  if (day) return `${Number(day[2])} ${formatMonth(day[1])}`;
  if (/^\d{4}-\d{2}$/.test(asOf)) return formatMonth(asOf);
  return asOf;
}

export function withKeys(sources: Record<string, Source>): Source[] {
  return Object.entries(sources).map(([key, source]) => ({ ...source, key }));
}

export type SourceGroup = {
  publisher: string;
  sources: Source[];
  /** True when every source in the group has the same licence and credit line, so they are shown once. */
  shared: boolean;
};

const dateKey = (source: Source) => (notStated(source.asOf) ? "" : (source.asOf ?? ""));

export function groupByPublisher(sources: Source[]): SourceGroup[] {
  const byPublisher = new Map<string, Source[]>();
  for (const source of sources) {
    const publisher = source.publisher ?? "not stated";
    byPublisher.set(publisher, [...(byPublisher.get(publisher) ?? []), source]);
  }

  return [...byPublisher]
    .map(([publisher, list]) => ({
      publisher,
      sources: [...list].sort((a, b) => dateKey(b).localeCompare(dateKey(a)) || a.title.localeCompare(b.title)),
      shared: list.length > 1 && list.every((s) => s.license === list[0].license && s.credit === list[0].credit),
    }))
    .sort(
      (a, b) => Number(notStated(a.publisher)) - Number(notStated(b.publisher)) || a.publisher.localeCompare(b.publisher),
    );
}
