import { formatCount, formatMonth, WATER_CLASS } from "@/lib/format";
import type { LakeSummary, LngLat, WaterClass } from "@/lib/lake";
import { distanceKm } from "./geo";
import { acresText, distanceText, pctText } from "./words";

/** In the order they are offered. Most polluted sits second so a phone reaches it in one tap. */
export const COLLECTION_KEYS = ["biggest", "polluted", "near", "built", "organising", "unlooked"] as const;

export type CollectionKey = (typeof COLLECTION_KEYS)[number];

export type Collection = {
  title: string;
  note: (count: number) => string;
  empty: string;
};

export type Ranked = { lake: LakeSummary; value?: string; detail?: string; km?: number };

export const COLLECTIONS: Record<CollectionKey, Collection> = {
  biggest: {
    title: "Biggest",
    note: (n) => `The ${formatCount(n)} largest lakes that still exist, in acres.`,
    empty: "No lake sizes are on record yet.",
  },
  polluted: {
    title: "Most polluted",
    note: (n) =>
      `Only the ${formatCount(n)} lakes the Karnataka State Pollution Control Board tests are ranked. Worst water class first, newest test first.`,
    empty: "No lake has a water test on record yet.",
  },
  near: {
    title: "Near me",
    note: (n) => `The ${formatCount(n)} lakes closest to you, in a straight line.`,
    empty: "No lake on record has a location yet.",
  },
  built: {
    title: "Most built over",
    note: () => "Share of each lake’s outline covered by buildings, measured from 2021 satellite land cover.",
    empty: "No built-over measurements are on record yet.",
  },
  organising: {
    title: "Residents organising",
    note: (n) => `${formatCount(n)} lakes where residents have a campaign on record, largest first.`,
    empty: "No residents’ campaigns are on record yet.",
  },
  unlooked: {
    title: "Nobody on record looks after it",
    note: (n) => `${formatCount(n)} lakes with no agency named as custodian in any list we have, largest first.`,
    empty: "Every lake on record has someone looking after it.",
  },
};

export function isCollectionKey(value: string | null): value is CollectionKey {
  return value !== null && (COLLECTION_KEYS as readonly string[]).includes(value);
}

const WORST_FIRST: Record<WaterClass, number> = { E: 0, D: 1, C: 2, B: 3, A: 4 };

const largestFirst = (a: LakeSummary, b: LakeSummary) => (b.acres ?? -1) - (a.acres ?? -1);

const bySize = (lake: LakeSummary): Ranked => ({ lake, value: acresText(lake) });

/** The ranked members of a collection. Near me is null until there is a location. */
export function rank(key: CollectionKey, lakes: LakeSummary[], here: LngLat | null): Ranked[] | null {
  switch (key) {
    case "biggest":
      return lakes
        .filter((lake) => lake.status === "exists" && lake.acres !== undefined)
        .sort(largestFirst)
        .slice(0, 50)
        .map(bySize);

    case "polluted":
      return lakes
        .flatMap((lake) => (lake.waterClass ? [{ lake, cls: lake.waterClass }] : []))
        .sort(
          (a, b) =>
            WORST_FIRST[a.cls] - WORST_FIRST[b.cls] ||
            (b.lake.waterClassMonth ?? "").localeCompare(a.lake.waterClassMonth ?? "") ||
            largestFirst(a.lake, b.lake),
        )
        .map(({ lake, cls }) => ({
          lake,
          value: `Class ${cls}`,
          detail: [WATER_CLASS[cls].short, lake.waterClassMonth && `tested ${formatMonth(lake.waterClassMonth)}`]
            .filter(Boolean)
            .join(", "),
        }));

    case "near": {
      if (!here) return null;
      return lakes
        .flatMap((lake) => (lake.status === "exists" && lake.point ? [{ lake, km: distanceKm(here, lake.point) }] : []))
        .sort((a, b) => a.km - b.km)
        .slice(0, 30)
        .map(({ lake, km }) => ({ lake, km, value: distanceText(km), detail: acresText(lake) }));
    }

    case "built":
      return lakes
        .filter((lake) => lake.status === "exists" && lake.hasOutline && (lake.builtPct ?? 0) >= 1)
        .sort((a, b) => (b.builtPct ?? 0) - (a.builtPct ?? 0))
        .slice(0, 50)
        .map((lake) => ({ lake, value: `${pctText(lake.builtPct ?? 0)} built over`, detail: acresText(lake) }));

    case "organising":
      return lakes.filter((lake) => lake.campaign).sort(largestFirst).map(bySize);

    case "unlooked":
      return lakes
        .filter((lake) => lake.status === "exists" && !lake.custodian)
        .sort(largestFirst)
        .map(bySize);
  }
}
