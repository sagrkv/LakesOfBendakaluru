import { joinList } from "../words";
import type { Entry } from "./types";

/**
 * The line runs from the oldest record to today. A stretch of this many years or more with nothing
 * on record is cut out and drawn as a short break, so the years that do have records get the room.
 */
const GAP_YEARS = 3;
/** How many years' width a break may take: narrow on phones, wider from 768 px. */
export const GAP_CAP = { phone: 3, wide: 12 } as const;

export type Segment = { kind: "years" | "gap"; from: number; to: number };

export function yearsOf(entry: Entry): number[] {
  if (entry.points) return entry.points;
  const to = entry.to ?? entry.from;
  return Array.from({ length: to - entry.from + 1 }, (_, i) => entry.from + i);
}

export function segmentsOf(entries: Entry[], now: number): Segment[] {
  const covered = new Set(entries.flatMap(yearsOf).filter((year) => year <= now));
  if (!covered.size) return [];
  const segments: Segment[] = [];
  const addYears = (from: number, to: number) => {
    const last = segments[segments.length - 1];
    if (last?.kind === "years" && last.to === from - 1) segments[segments.length - 1] = { ...last, to };
    else segments.push({ kind: "years", from, to });
  };

  let year = Math.min(...covered);
  while (year <= now) {
    const has = covered.has(year);
    let end = year;
    while (end + 1 <= now && covered.has(end + 1) === has) end += 1;
    if (!has && end - year + 1 >= GAP_YEARS) segments.push({ kind: "gap", from: year, to: end });
    else addYears(year, end);
    year = end + 1;
  }
  return segments;
}

export function unitsOf(segment: Segment, cap: number): number {
  const years = segment.to - segment.from + 1;
  return segment.kind === "years" ? years : Math.min(years, cap);
}

/** Grid columns: a years column never narrower than its label, a break never narrower than a cut. */
export function columnsOf(segments: Segment[], cap: number): string {
  return segments
    .map((s, i) => {
      const min = s.kind === "years" ? 32 : i === segments.length - 1 ? 40 : 12;
      return `minmax(${min}px, ${unitsOf(s, cap)}fr)`;
    })
    .join(" ");
}

export function segmentIndex(segments: Segment[], year: number): number {
  return segments.findIndex((s) => s.kind === "years" && year >= s.from && year <= s.to);
}

/** Left edge and width of a run of years inside its column, as percentages. */
export function placeIn(segment: Segment, from: number, to = from): { left: string; width: string } {
  const units = segment.to - segment.from + 1;
  return { left: `${((from - segment.from) / units) * 100}%`, width: `${((to - from + 1) / units) * 100}%` };
}

/** How far along the whole line a year sits, 0 to 1, on the phone layout. Used to open hover tags inward. */
export function fractionOf(segments: Segment[], year: number): number {
  const total = segments.reduce((sum, s) => sum + unitsOf(s, GAP_CAP.phone), 0);
  let before = 0;
  for (const s of segments) {
    if (s.kind === "years" && year >= s.from && year <= s.to) return (before + year - s.from + 0.5) / total;
    before += unitsOf(s, GAP_CAP.phone);
  }
  return 0;
}

/** Which row of the records lane each entry takes, so pieces a year apart never touch. */
export function stackRows(entries: Entry[], segments: Segment[]): { rows: Map<string, number>; count: number } {
  const ends: number[] = [];
  const rows = new Map<string, number>();
  const at = (year: number) => fractionOf(segments, year);
  const sorted = [...entries].sort((a, b) => Math.min(...yearsOf(a)) - Math.min(...yearsOf(b)));
  const total = segments.reduce((sum, s) => sum + unitsOf(s, GAP_CAP.phone), 0) || 1;
  for (const entry of sorted) {
    const years = yearsOf(entry);
    const start = at(Math.min(...years)) * total - 0.5;
    const end = at(Math.max(...years)) * total + 0.5;
    const free = ends.findIndex((last) => last + 1 <= start);
    const row = free === -1 ? ends.length : free;
    ends[row] = end;
    rows.set(entry.id, row);
  }
  return { rows, count: Math.max(1, ends.length) };
}

/** Every break in the record, said once. */
export function gapSentence(segments: Segment[], now: number): string | undefined {
  const gaps = segments.filter((s) => s.kind === "gap");
  if (!gaps.length) return undefined;
  const inner = gaps.filter((g) => g.to < now).map((g) => `${g.from} to ${g.to}`);
  const tail = gaps.find((g) => g.to === now);
  if (!inner.length) return `Nothing on record since ${tail!.from - 1}.`;
  return `Nothing on record for ${joinList(inner)}${tail ? `, and nothing since ${tail.from - 1}` : ""}.`;
}
