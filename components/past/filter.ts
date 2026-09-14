/** Choosing lakes by when they went, what stands there now and who filled them in. Safe in the browser. */

import { formatCount } from "@/lib/format";
import { OCCUPIED, occupiedId, type OccupiedId } from "./occupied";
import type { PastLake } from "./types";
import { parseWhen, whenOf, whenPhrase, type When } from "./when";
import { WHO, whoIds, type WhoId } from "./who";

export type Tagged = PastLake & { when: When; now: OccupiedId; who: WhoId[] };
export type Filter = { when: string | null; now: OccupiedId | null; who: WhoId | null };
export type Counts = { when: Record<string, number>; now: Partial<Record<OccupiedId, number>>; who: Partial<Record<WhoId, number>> };

export const NO_FILTER: Filter = { when: null, now: null, who: null };

export function tag(lake: PastLake): Tagged {
  return { ...lake, when: whenOf(lake), now: occupiedId(lake.nowOccupiedBy), who: whoIds(lake.convertedBy) };
}

export function isFiltered(filter: Filter): boolean {
  return Boolean(filter.when || filter.now || filter.who);
}

export function matches(lake: Tagged, filter: Filter): boolean {
  return (
    (!filter.when || lake.when.id === filter.when) &&
    (!filter.now || lake.now === filter.now) &&
    (!filter.who || lake.who.includes(filter.who))
  );
}

/** How many lakes fall in each bar. A lake that names several parties counts once for each. */
export function tally(lakes: Tagged[]): Counts {
  const counts: Counts = { when: {}, now: {}, who: {} };
  for (const lake of lakes) {
    counts.when[lake.when.id] = (counts.when[lake.when.id] ?? 0) + 1;
    counts.now[lake.now] = (counts.now[lake.now] ?? 0) + 1;
    for (const id of lake.who) counts.who[id] = (counts.who[id] ?? 0) + 1;
  }
  return counts;
}

/** "the 12 lakes gone by 2016, now houses or layouts, filled in by farmers". */
export function describe(filter: Filter, count: number): string {
  const parts = [
    filter.when && whenPhrase(parseWhen(filter.when)),
    filter.now && OCCUPIED.find((group) => group.id === filter.now)?.phrase,
    filter.who && WHO.find((group) => group.id === filter.who)?.phrase,
  ]
    .filter(Boolean)
    .join(", ");
  return count === 1 ? `the one lake ${parts}`.replace(" them ", " it ") : `the ${formatCount(count)} lakes ${parts}`;
}
