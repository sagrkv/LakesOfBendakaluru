import { readFileSync } from "node:fs";
import { join } from "node:path";
import { getSources } from "@/lib/lakes";
import type { Copy, Resolved, TimelineSource } from "./types";

/** Our copies of each record, by source id, as scripts/archive.py last wrote them. */
function readArchive(): Record<string, Copy[]> {
  const file = join(/* turbopackIgnore: true */ process.cwd(), "public", "data", "archive.json");
  return JSON.parse(readFileSync(file, "utf8")) as Record<string, Copy[]>;
}

/**
 * Turns source keys into the addresses sources.json holds, and attaches our copies, on the server.
 * A key with no address is dropped rather than shown as a dead link.
 */
export function resolveSources(list: TimelineSource[]): Resolved[] {
  const cited = getSources();
  const archive = readArchive();
  return list.map(({ links, ...source }) => {
    const keys = links.flatMap((link) => ("key" in link && cited[link.key] ? [link.key] : []));
    return {
      ...source,
      links: links.flatMap((link) => {
        if ("href" in link) return [link];
        const href = cited[link.key]?.url;
        return href ? [{ label: link.label, href }] : [];
      }),
      copies: archive[source.id] ?? [],
      sourcesAnchor: keys[0],
    };
  });
}
