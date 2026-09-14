/** One row of public/data/past.json, written by scripts/assemble/past.py. Unknown facts are left out. */
export type PastLake = {
  id: string;
  name: string;
  acres?: number;
  valley?: string;
  /** Position in the hero.json frame. */
  xy?: [number, number];
  /** The 2018 lake survey found it gone by this year. */
  goneBy?: number;
  /** The last year satellite images show water here. */
  lastSeenWithWater?: number;
  /** Years of the old survey maps it is drawn on. */
  onMap?: number[];
  knownOnlyFromOldMap?: true;
  convertedBy?: string[];
  nowOccupiedBy?: string;
};
