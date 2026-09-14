import { getSources } from "@/lib/lakes";
import type { Resolved, TimelineSource } from "./types";

/**
 * Turns source keys into the addresses sources.json holds, on the server.
 * A key with no address is dropped rather than shown as a dead link.
 */
export function resolveSources(list: TimelineSource[]): Resolved[] {
  const cited = getSources();
  return list.map(({ links, ...source }) => {
    const keys = links.flatMap((link) => ("key" in link && cited[link.key] ? [link.key] : []));
    return {
      ...source,
      links: links.flatMap((link) => {
        if ("href" in link) return [link];
        const href = cited[link.key]?.url;
        return href ? [{ label: link.label, href }] : [];
      }),
      sourcesAnchor: keys[0],
    };
  });
}
