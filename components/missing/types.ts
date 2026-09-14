import type { Kind } from "@/lib/lake";

/** One row of public/data/missing.json, written by scripts/assemble/missing.py. Unknown facts are left out. */
export type MissingLake = {
  id: string;
  name: string;
  nameKannada?: string;
  kind?: Kind;
  /** The extent the 2018 lake survey recorded. */
  acres?: number;
  village?: string;
  taluk?: string;
  ward?: string;
  custodian?: string;
  condition2018?: string[];
  uses2018?: string[];
  /** Named on the 2024 KTCDA list of lakes. */
  onList2024?: true;
  /** Its page on the city's lake monitoring site. */
  monitoringPage?: string;
  /** The last year satellites saw water here. */
  waterSeen?: number;
  /** Years of the old survey maps it is drawn on. */
  onMap?: number[];
  /** Position in the hero.json frame. */
  xy?: [number, number];
};
