import { GAPS } from "./gaps";
import type { Gap, Resolved } from "./types";

export type Row =
  | { type: "century"; label: string }
  | { type: "year"; year: number; records: Resolved[] }
  | { type: "gap"; gap: Gap }
  | { type: "undated"; records: Resolved[] };

/**
 * The timeline top to bottom, from records already sorted oldest first: a heading where a century starts,
 * one row per year that has records, each named gap before the first year after it starts, then the records with no year.
 */
export function rowsOf(sources: Resolved[]): Row[] {
  const rows: Row[] = [];
  let gap = 0;
  let century: number | undefined;

  for (const source of sources) {
    const year = source.from;
    if (year === undefined) continue;
    for (; gap < GAPS.length && GAPS[gap].from < year; gap++) rows.push({ type: "gap", gap: GAPS[gap] });

    const last = rows.at(-1);
    if (last?.type === "year" && last.year === year) {
      last.records.push(source);
      continue;
    }
    const start = Math.floor(year / 100) * 100;
    if (start !== century) {
      century = start;
      rows.push({ type: "century", label: `${start}s` });
    }
    rows.push({ type: "year", year, records: [source] });
  }

  const undated = sources.filter((source) => source.from === undefined);
  if (undated.length) rows.push({ type: "undated", records: undated });
  return rows;
}
