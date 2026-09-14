/** Plain lines for what the record says about a missing lake. Safe in the browser. */

import { joinList, sentence } from "@/components/lake/words";
import { SURVEY_YEAR } from "./filter";
import type { MissingLake } from "./types";

const KIND: Record<string, string> = {
  kere: "Kere, a large tank",
  katte: "Katte, a medium tank",
  kunte: "Kunte, a small pond",
};

/** The survey writes a condition as one word; these read better after "it was". */
const CONDITION: Record<string, string> = {
  sewage: "taking in sewage",
  "green water": "green",
  puddle: "a puddle",
};

/** Survey spellings tidied for reading. */
const USE: Record<string, string> = {
  "ground waterrecharg": "groundwater recharge",
};

function use(word: string): string {
  const lower = word.trim().toLowerCase();
  return USE[lower] ?? lower;
}

export function kindLine(kind: MissingLake["kind"]): string | null {
  return kind ? KIND[kind] : null;
}

/** "Muddy and polluted in 2018, used for cattle feeding"; null when the survey noted neither. */
export function surveyLine(lake: MissingLake): string | null {
  const condition = lake.condition2018?.length
    ? `${joinList(lake.condition2018.map((word) => CONDITION[word] ?? word))} in 2018`
    : null;
  const uses = lake.uses2018?.length ? `used for ${joinList([...new Set(lake.uses2018.map(use))])}` : null;
  if (!condition && !uses) return null;
  return sentence([condition, uses].filter(Boolean).join(", "));
}

export function placeLine(lake: MissingLake): string | null {
  const parts = [lake.village, lake.taluk ? `${lake.taluk} taluk` : undefined].filter(Boolean);
  return parts.length ? parts.join(", ") : null;
}

/** Satellite water, split at the survey year: after it is newer evidence, before it is not. */
export function waterLine(waterSeen: number | undefined): string | null {
  if (!waterSeen) return null;
  return waterSeen > SURVEY_YEAR
    ? `Satellites saw water near here in ${waterSeen}`
    : `Satellites last saw water near here in ${waterSeen}`;
}

/** `printed` is the real print year of each sheet that draws it, when that differs from the edition year. */
export function mapLine(onMap: number[] | undefined, printed?: number[]): string | null {
  const years = printed ?? onMap;
  if (!years?.length) return null;
  return `Drawn on the ${joinList(years.map(String))} survey map${years.length > 1 ? "s" : ""}`;
}
