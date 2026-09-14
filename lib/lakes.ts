/** Server-only readers for public/data. Pages read these at build or request time. */

import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import type { Hero, LakeRecord, LakeSummary, Source } from "./lake";

// Read at runtime from disk; the ignore comment keeps the bundler from tracing all 2,700 lake files.
const dataDir = join(/* turbopackIgnore: true */ process.cwd(), "public", "data");

function read<T>(file: string): T {
  return JSON.parse(readFileSync(join(dataDir, file), "utf8")) as T;
}

let lakes: LakeSummary[] | null = null;
let byId: Map<string, LakeSummary> | null = null;
let sources: Record<string, Source> | null = null;
let openers: string[] | null = null;

/** Every lake, largest first. */
export function getLakes(): LakeSummary[] {
  lakes ??= read<LakeSummary[]>("lakes.json");
  return lakes;
}

export function getSummary(id: string): LakeSummary | undefined {
  byId ??= new Map(getLakes().map((lake) => [lake.id, lake]));
  return byId.get(id);
}

/** The full record for one lake page. Ids come from URLs, so only plain slugs are read. */
export function getLake(id: string): LakeRecord | undefined {
  if (!/^[a-z0-9-]+$/.test(id)) return undefined;
  const file = join("lake", `${id}.json`);
  if (!existsSync(join(dataDir, file))) return undefined;
  return read<LakeRecord>(file);
}

export function getSources(): Record<string, Source> {
  sources ??= read<Record<string, Source>>("sources.json");
  return sources;
}

export function getSource(key: string): Source | undefined {
  return getSources()[key];
}

/** Lakes whose shape leaves room for their name on the opening screen. */
export function getOpeners(): string[] {
  openers ??= read<string[]>("openers.json");
  return openers;
}

export function getHero(): Hero {
  return read<Hero>("hero.json");
}
