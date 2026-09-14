import type { LakeRecord, LakeSummary, Sheet } from "@/lib/lake";
import { getHero, getLake, getLakes, getOpeners, getSummary } from "@/lib/lakes";
import { fitName, type NameFit } from "./fit";

/** What the locator and the rank slip need about every lake. */
export type City = { width: number; height: number; dots: string; ranked: number };

export type Opener = {
  lake: LakeRecord & { sheet: Sheet };
  summary: LakeSummary;
  fit: NameFit;
  city: City;
};

/** About one opener in twelve has a name that cannot fit; this many tries all but never comes up empty. */
const TRIES = 24;

let city: City | null = null;

/** Every lake as a dot in the hero.json frame, built once per server process. */
function getCity(): City {
  if (city) return city;
  const lakes = getLakes();
  const { width, height } = getHero();
  const dots = lakes
    .flatMap((lake) => (lake.xy ? [`M${Math.round(lake.xy[0])} ${Math.round(lake.xy[1])}h0`] : []))
    .join("");
  const ranked = lakes.reduce((most, lake) => Math.max(most, lake.sizeRank ?? 0), 0);
  city = { width, height, dots, ranked };
  return city;
}

/**
 * A random lake that can open the site: it has a cut-out and its name fits the room.
 * Undefined when there is none, including while the data files are being rebuilt.
 */
export function pickOpener(): Opener | undefined {
  try {
    const ids = getOpeners();
    for (let i = 0; i < Math.min(TRIES, ids.length * 2); i++) {
      const id = ids[Math.floor(Math.random() * ids.length)];
      const lake = getLake(id);
      const summary = getSummary(id);
      if (!lake?.sheet || !summary) continue;
      const fit = fitName(lake.name, lake.sheet.room, lake.nameKannada);
      if (!fit) continue;
      return { lake: { ...lake, sheet: lake.sheet }, summary, fit, city: getCity() };
    }
    return undefined;
  } catch {
    // A missing or half-written data file: show the empty opening rather than an error page.
    return undefined;
  }
}
