import type { LakeRecord, Source } from "@/lib/lake";
import { getLake } from "@/lib/lakes";
import { resolve } from "../sources";
import type { Entry } from "./types";

/** Server only: sheet citations come from sources.json. */

type History = LakeRecord["history"];

const EDITIONS = [1914, 1927, 1945, 1955, 1975] as const;
type Edition = (typeof EDITIONS)[number];

type MapRecord = { edition: Edition; drawn: boolean; years: number[]; keys: string[]; sources: Source[] };

function keysOf(h: NonNullable<History>, fact: string): string[] {
  const key = h.src[fact];
  if (!key || key === "per-entry") return [];
  return Array.isArray(key) ? key : [key];
}

/**
 * What each map edition says about the lake, with the year its sheets were really printed.
 * An edition with no answer (the sheet does not cover it, or no confident match) is left out, never shown as not drawn.
 */
function mapRecords(h: History): MapRecord[] {
  if (!h) return [];
  return EDITIONS.flatMap((edition) => {
    const drawn = h[`onMap${edition}`];
    if (drawn === undefined) return [];
    const keys = keysOf(h, `onMap${edition}`);
    const sources = resolve(keys);
    const printed = sources.map((source) => Number.parseInt(source.asOf ?? "", 10)).filter(Number.isFinite);
    const years = printed.length ? [...new Set(printed)].sort((a, b) => a - b) : [edition];
    return [{ edition, drawn, years, keys, sources }];
  });
}

/** Print years of every sheet that draws the lake, oldest first. */
export function printedYears(h: History): number[] {
  const years = mapRecords(h).flatMap((record) => (record.drawn ? record.years : []));
  return [...new Set(years)].sort((a, b) => a - b);
}

/** For list rows that only carry edition years: the real print years, for rows on a 1914 or 1975 edition. */
export function printedYearsFor(rows: { id: string; onMap?: number[] }[]): Record<string, number[]> {
  return Object.fromEntries(
    rows.flatMap((row) => {
      if (!row.onMap?.some((year) => year === 1914 || year === 1975)) return [];
      const years = printedYears(getLake(row.id)?.history);
      return years.length ? [[row.id, years]] : [];
    }),
  );
}

export function mapEntries(h: History): Entry[] {
  const records = mapRecords(h);
  const oldMapKeys = h ? keysOf(h, "knownOnlyFromOldMap") : [];
  const traced = h?.knownOnlyFromOldMap
    ? (records.find((r) => r.drawn && r.keys.some((key) => oldMapKeys.includes(key))) ?? records.find((r) => r.drawn))
    : undefined;

  return records.map((record) => {
    const army = record.edition === 1955;
    const map = `${army ? "U.S. Army" : "survey"} map${record.sources.length > 1 ? "s" : ""}`;
    const notes: string[] = [];
    if (army) notes.push("Compiled from Survey of India maps of 1945-46");
    if (record === traced) {
      notes.push(`Known only from this map, and the match to it is ${h?.oldMapConfidence === "high" ? "sure" : "likely"}`);
    }
    return {
      id: `map-${record.edition}`,
      from: record.years[0],
      points: record.years,
      when: record.years.join(" and "),
      label: record.drawn ? `On the ${map}` : `Not on the ${map}`,
      notes,
      sources: record.sources,
      lane: "records",
      tone: record.drawn ? "lake" : "no-lake",
    };
  });
}
