import type { LakeRecord } from "@/lib/lake";
import { NOW } from "@/components/timeline/gaps";
import { mapEntries } from "./maps";
import { rauEntry } from "./rau";
import { recordEntries } from "./records";
import type { Entry } from "./types";
import { waterEntries } from "./water";

/** Every dated fact about a lake, oldest first. Server only. */
export function entriesOf(lake: LakeRecord): Entry[] {
  return [...mapEntries(lake.history), ...rauEntry(lake.history), ...recordEntries(lake), ...waterEntries(lake)]
    .filter((entry) => entry.from <= NOW)
    .sort((a, b) => a.from - b.from || (a.to ?? a.from) - (b.to ?? b.from));
}
