import type { Kind, Resolved } from "./types";
import { KINDS } from "./words";

/** The axis runs a few years either side of 1800 and today, so the first and last marks are not cut. */
export const START = 1795;
export const END = 2030;

/** Where a year sits along the axis, 0 to 1. */
export function at(year: number): number {
  return (year - START) / (END - START);
}

export const TICKS = Array.from({ length: 10 }, (_, i) => 1800 + i * 25);

/** Two marks in one row keep this many years apart, so the narrowest laptop still shows a gap between them. */
const SPACING = 5;

export type Placed = {
  source: Resolved;
  /** Position in time order, for moving between marks with the arrow keys. */
  index: number;
  a: number;
  len: number;
  row: number;
  /** For sources with no year: which step of the no-year column. */
  step: number;
};

export type Lane = { kind: Kind; name: string; rows: number; dated: Placed[]; undated: Placed[] };

/**
 * Sorts each kind into its lane and each source into the first row where it does not touch the one before.
 * Sources with no year on record fill the lane's rows in turn, one step further out each time the rows are full.
 */
export function layoutLanes(sources: Resolved[]): { lanes: Lane[]; steps: number } {
  const lanes = KINDS.map(({ kind, name }) => {
    const mine = sources.map((source, index) => ({ source, index })).filter(({ source }) => source.kind === kind);
    const ends: number[] = [];

    const dated = mine.flatMap(({ source, index }): Placed[] => {
      if (source.from === undefined) return [];
      const from = source.from;
      const end = (source.to ?? from) + 1;
      const free = ends.findIndex((last) => last <= from);
      const row = free === -1 ? ends.length : free;
      ends[row] = Math.max(end, from + SPACING - 1) + 1;
      return [{ source, index, a: at(from), len: (end - from) / (END - START), row, step: 0 }];
    });

    const rows = Math.max(1, ends.length);
    const undated = mine
      .filter(({ source }) => source.from === undefined)
      .map(({ source, index }, i) => ({ source, index, a: 0, len: 0, row: i % rows, step: Math.floor(i / rows) }));

    return { kind, name, rows, dated, undated };
  });

  const steps = Math.max(1, ...lanes.map((lane) => Math.ceil(lane.undated.length / lane.rows)));
  return { lanes, steps };
}
