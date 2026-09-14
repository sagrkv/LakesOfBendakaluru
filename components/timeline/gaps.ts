import type { Gap } from "./types";

/** The year the research was done; spans that run "to now" end here. */
export const NOW = 2026;

/** Stretches the record barely covers, named on the timeline. */
export const GAPS: Gap[] = [
  { from: 1808, to: 1843, years: "1808 to 1843", text: "Nothing on record." },
  {
    from: 1955,
    to: 1984,
    years: "1955 to 1984",
    text: "Maps from the 1970s draw the tanks, but only spy satellite photos show whether small ponds held water.",
  },
];
