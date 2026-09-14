/** Server-only: the missing lakes, read from disk when the page is rendered. */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { MissingLake } from "./types";

let missing: MissingLake[] | null = null;

/** Every lake recorded as existing that no map draws, largest first. */
export function getMissing(): MissingLake[] {
  missing ??= JSON.parse(
    readFileSync(join(/* turbopackIgnore: true */ process.cwd(), "public", "data", "missing.json"), "utf8"),
  ) as MissingLake[];
  return missing;
}
