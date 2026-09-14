import { CENSUSES } from "./sources-counts";
import { MAPS } from "./sources-maps";
import { REPORTS } from "./sources-reports";
import { SATELLITES } from "./sources-satellites";
import type { TimelineSource } from "./types";

/**
 * Every record of Bengaluru's lakes we know of, oldest first, then the ones with no year on record.
 * Server only: the page resolves links and hands the timeline what it draws.
 */
export const SOURCES: TimelineSource[] = [...MAPS, ...CENSUSES, ...SATELLITES, ...REPORTS].sort(
  (a, b) => (a.from ?? Infinity) - (b.from ?? Infinity) || (a.to ?? a.from ?? 0) - (b.to ?? b.from ?? 0),
);
