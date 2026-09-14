import type { Status, TimelineSource } from "./types";

/** The intro's facts, counted from the source list. */
export function tally(sources: TimelineSource[]) {
  const dated = sources.filter((source) => source.from !== undefined);
  const counts: Record<Status, number> = { "on-site": 0, found: 0, "not-public": 0 };
  for (const source of sources) counts[source.status] += 1;

  return {
    total: sources.length,
    counts,
    undated: sources.length - dated.length,
    oldest: Math.min(...dated.map((source) => source.from ?? Infinity)),
    newest: Math.max(...dated.map((source) => source.to ?? source.from ?? -Infinity)),
    oldestOnSite: Math.min(
      ...dated.filter((source) => source.status === "on-site").map((source) => source.from ?? Infinity),
    ),
  };
}
