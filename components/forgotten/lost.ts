/** Server-side reading for the Forgotten Lakes page: every lake on record as gone, counted and placed. */

import type { LakeSummary } from "@/lib/lake";
import { getHero, getLakes } from "@/lib/lakes";
import { OCCUPIED, occupiedId, type Occupied, type OccupiedId } from "./occupied";

export type LostLake = LakeSummary & { occupied: OccupiedId };
export type OccupiedCount = Occupied & { count: number };
export type Hole = { id: string; x: number; y: number; r: number };

const SQ_M_PER_ACRE = 4046.86;
/** Holes are drawn this many times wider than the lake was, so half-acre ponds still show. */
export const HOLE_WIDENING = 6;
/** Radius in frame units for a lake with no recorded extent. */
const MIN_HOLE = 1.5;

export function getLost() {
  const lost: LostLake[] = getLakes()
    .filter((lake) => lake.status !== "exists")
    .map((lake) => ({ ...lake, occupied: occupiedId(lake.nowOccupiedBy) }))
    .sort((a, b) => (b.acres ?? -1) - (a.acres ?? -1) || a.name.localeCompare(b.name));

  const acres = lost.reduce((sum, lake) => sum + (lake.acres ?? 0), 0);
  const withoutExtent = lost.filter((lake) => !lake.acres).length;

  // Largest group first; "something else" and "not on record" always close the list.
  const counts: OccupiedCount[] = OCCUPIED.map((group) => ({
    ...group,
    count: lost.filter((lake) => lake.occupied === group.id).length,
  }))
    .filter((group) => group.count > 0)
    .sort((a, b) => Number(a.id === "other" || a.id === "none") - Number(b.id === "other" || b.id === "none") || b.count - a.count);

  return { lost, acres, withoutExtent, counts };
}

/** Metres per hero.json unit, measured between the westernmost and easternmost placed lakes. */
function metresPerUnit(lakes: LakeSummary[]): number {
  const placed = lakes.filter((lake) => lake.xy && lake.point);
  let west = placed[0];
  let east = placed[0];
  for (const lake of placed) {
    if (lake.point![0] < west.point![0]) west = lake;
    if (lake.point![0] > east.point![0]) east = lake;
  }
  const lat = ((west.point![1] + east.point![1]) / 2) * (Math.PI / 180);
  const metres = (east.point![0] - west.point![0]) * 111320 * Math.cos(lat);
  return metres / (east.xy![0] - west.xy![0]);
}

const round = (n: number) => Math.round(n * 10) / 10;

/** The city as one sheet: a hole where each lost lake was, a dot where each lake still is. */
export function getPunchedCity(lost: LostLake[]) {
  const { width, height } = getHero();
  const lakes = getLakes();
  const perUnit = metresPerUnit(lakes);

  const holes: Hole[] = lost
    .filter((lake) => lake.xy)
    .map((lake) => {
      const radiusM = lake.acres ? Math.sqrt((lake.acres * SQ_M_PER_ACRE) / Math.PI) : 0;
      return {
        id: lake.id,
        x: round(lake.xy![0]),
        y: round(lake.xy![1]),
        r: round(Math.max(MIN_HOLE, (radiusM * HOLE_WIDENING) / perUnit)),
      };
    });

  const dots = lakes
    .filter((lake) => lake.status === "exists" && lake.xy)
    .map((lake) => ({ id: lake.id, x: round(lake.xy![0]), y: round(lake.xy![1]) }));

  return { width, height, holes, dots };
}
