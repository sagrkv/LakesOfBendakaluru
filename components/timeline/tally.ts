import type { Kind, TimelineSource } from "./types";

/** The intro's facts, counted from the source list. */
export function tally(sources: TimelineSource[]) {
  const dated = sources.filter((source) => source.from !== undefined);
  const counts: Record<Kind, number> = { map: 0, census: 0, satellite: 0, report: 0 };
  for (const source of sources) counts[source.kind] += 1;

  return {
    total: sources.length,
    counts,
    oldest: Math.min(...dated.map((source) => source.from ?? Infinity)),
    newest: Math.max(...dated.map((source) => source.to ?? source.from ?? -Infinity)),
  };
}
