/**
 * When a lake went, from the best dated evidence on record, never guessed.
 * The 2018 survey's "gone by" year comes first, then the last year satellites saw water,
 * then the latest old survey map it is drawn on.
 */

import { joinList } from "@/components/lake/words";
import type { PastLake } from "./types";

export type WhenKind = "map" | "satellite" | "survey" | "none";
/** `year` is the map year, the decade of last water, or the gone-by year. */
export type When = { id: string; kind: WhenKind; year?: number };

export const WHEN_GROUPS: { kind: WhenKind; title: string }[] = [
  { kind: "map", title: "Last drawn on an old survey map" },
  { kind: "satellite", title: "Last seen with water, by satellite" },
  { kind: "survey", title: "Gone by, says the 2018 lake survey" },
  { kind: "none", title: "No date" },
];

const at = (kind: WhenKind, year: number): When => ({ id: `${kind}-${year}`, kind, year });
const NONE: When = { id: "none", kind: "none" };

export function whenOf(lake: PastLake): When {
  if (lake.goneBy !== undefined) return at("survey", lake.goneBy);
  if (lake.lastSeenWithWater !== undefined) return at("satellite", Math.floor(lake.lastSeenWithWater / 10) * 10);
  if (lake.onMap?.length) return at("map", Math.max(...lake.onMap));
  return NONE;
}

export function parseWhen(id: string): When {
  const [kind, year] = id.split("-");
  return year ? at(kind as WhenKind, Number(year)) : NONE;
}

/** The line in a lake's row; null when nothing on record dates it. */
export function whenLine(lake: PastLake): string | null {
  const { kind } = whenOf(lake);
  if (kind === "survey") return `Gone by ${lake.goneBy}`;
  if (kind === "satellite") return `Last seen with water in ${lake.lastSeenWithWater}`;
  if (kind === "map") {
    const maps = lake.onMap!;
    return `On the ${joinList(maps.map(String))} survey map${maps.length > 1 ? "s" : ""}, not on today's`;
  }
  return null;
}

/** A bar's label under its group title. */
export function whenLabel(when: When): string {
  if (when.kind === "satellite") return `In the ${when.year}s`;
  if (when.kind === "none") return "Nothing on record dates them";
  return String(when.year);
}

/** Finishes "Showing the 12 lakes ...". */
export function whenPhrase(when: When): string {
  if (when.kind === "survey") return `gone by ${when.year}`;
  if (when.kind === "satellite") return `last seen with water in the ${when.year}s`;
  if (when.kind === "map") return `last drawn on the ${when.year} survey map`;
  return "with no date on record";
}
