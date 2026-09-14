import type { Source, Src } from "@/lib/lake";
import { getSource } from "@/lib/lakes";

/** Citations for one or more facts of a section, resolved from its `src` map. Server only. */
export function sourcesOf(section: { src: Src } | undefined, ...facts: string[]): Source[] {
  if (!section) return [];
  const keys = facts.flatMap((fact) => {
    const key = section.src[fact];
    if (!key || key === "per-entry") return [];
    return Array.isArray(key) ? key : [key];
  });
  return resolve(keys);
}

/** Citations for per-entry items, which carry their own source key. */
export function resolve(keys: (string | undefined)[]): Source[] {
  const unique = [...new Set(keys.filter((key): key is string => Boolean(key)))];
  return unique.map(getSource).filter((source): source is Source => Boolean(source));
}
