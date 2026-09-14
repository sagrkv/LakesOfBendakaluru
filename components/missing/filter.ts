/** Choosing missing lakes by taluk, by 2018 size and by whether anything newer is on record. Safe in the browser. */

import { formatCount } from "@/lib/format";
import type { MissingLake } from "./types";

export type SizeId = "under-two-thirds" | "up-to-2" | "up-to-10" | "10-plus" | "none";
export type NewerId = "some" | "none";

export type Tagged = MissingLake & { size: SizeId; newer: NewerId };
export type Filter = { taluk: string | null; size: SizeId | null; newer: NewerId | null };
export type Counts = { taluk: Record<string, number>; size: Partial<Record<SizeId, number>>; newer: Partial<Record<NewerId, number>> };

export const NO_FILTER: Filter = { taluk: null, size: null, newer: null };
export const NO_TALUK = "none";

/** `phrase` finishes "Showing the 12 lakes ...". */
export const SIZES: { id: SizeId; label: string; phrase: string }[] = [
  { id: "under-two-thirds", label: "Under two-thirds of an acre", phrase: "under two-thirds of an acre" },
  { id: "up-to-2", label: "Two-thirds of an acre to 2 acres", phrase: "of two-thirds of an acre to 2 acres" },
  { id: "up-to-10", label: "2 to 10 acres", phrase: "of 2 to 10 acres" },
  { id: "10-plus", label: "10 acres or more", phrase: "of 10 acres or more" },
  { id: "none", label: "No extent on record", phrase: "with no extent on record" },
];

export const NEWER: { id: NewerId; label: string; phrase: string }[] = [
  { id: "some", label: "Something on record since 2018", phrase: "with something on record since 2018" },
  { id: "none", label: "Nothing on record since 2018", phrase: "with nothing on record since 2018" },
];

/** The survey was 2018, so water seen by satellite counts as newer only from 2019. */
export const SURVEY_YEAR = 2018;

export function hasNewer(lake: MissingLake): boolean {
  return Boolean(lake.onList2024 || lake.monitoringPage || (lake.waterSeen && lake.waterSeen > SURVEY_YEAR));
}

function sizeOf(acres: number | undefined): SizeId {
  if (!acres) return "none";
  if (acres < 2 / 3) return "under-two-thirds";
  if (acres < 2) return "up-to-2";
  if (acres < 10) return "up-to-10";
  return "10-plus";
}

export function tag(lake: MissingLake): Tagged {
  return { ...lake, size: sizeOf(lake.acres), newer: hasNewer(lake) ? "some" : "none" };
}

export function isFiltered(filter: Filter): boolean {
  return Boolean(filter.taluk || filter.size || filter.newer);
}

export function matches(lake: Tagged, filter: Filter): boolean {
  return (
    (!filter.taluk || (lake.taluk ?? NO_TALUK) === filter.taluk) &&
    (!filter.size || lake.size === filter.size) &&
    (!filter.newer || lake.newer === filter.newer)
  );
}

export function tally(lakes: Tagged[]): Counts {
  const counts: Counts = { taluk: {}, size: {}, newer: {} };
  for (const lake of lakes) {
    const taluk = lake.taluk ?? NO_TALUK;
    counts.taluk[taluk] = (counts.taluk[taluk] ?? 0) + 1;
    counts.size[lake.size] = (counts.size[lake.size] ?? 0) + 1;
    counts.newer[lake.newer] = (counts.newer[lake.newer] ?? 0) + 1;
  }
  return counts;
}

/** "the 12 lakes in Anekal taluk, under two-thirds of an acre, with nothing on record since 2018". */
export function describe(filter: Filter, count: number): string {
  const parts = [
    filter.taluk && (filter.taluk === NO_TALUK ? "with no taluk on record" : `in ${filter.taluk} taluk`),
    filter.size && SIZES.find((group) => group.id === filter.size)?.phrase,
    filter.newer && NEWER.find((group) => group.id === filter.newer)?.phrase,
  ]
    .filter(Boolean)
    .join(", ");
  return count === 1 ? `the one lake ${parts}` : `the ${formatCount(count)} lakes ${parts}`;
}
