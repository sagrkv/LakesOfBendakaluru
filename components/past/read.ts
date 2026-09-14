/** Server-only: the past lakes, read from disk when the page is rendered. */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { PastLake } from "./types";

let past: PastLake[] | null = null;

/** Every lake that is gone, largest first. */
export function getPast(): PastLake[] {
  past ??= JSON.parse(
    readFileSync(join(/* turbopackIgnore: true */ process.cwd(), "public", "data", "past.json"), "utf8"),
  ) as PastLake[];
  return past;
}
