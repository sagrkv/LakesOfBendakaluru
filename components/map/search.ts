import type { LakeSummary } from "@/lib/lake";

type Row = { lake: LakeSummary; name: string; kannada: string; ward: string };

export type SearchIndex = Row[];
export type SearchHit = { lake: LakeSummary; byWard: boolean };
export type SearchResult = { hits: SearchHit[]; total: number };

/** Lower case, Latin accents removed. Kannada is left whole. */
function fold(text: string): string {
  return text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

export function buildIndex(lakes: LakeSummary[]): SearchIndex {
  return lakes.map((lake) => ({
    lake,
    name: fold(lake.name),
    kannada: fold(lake.nameKannada ?? ""),
    ward: fold(lake.ward ?? ""),
  }));
}

export const MIN_QUERY = 2;

/** Name matches beat ward matches; a name that starts with the query beats one that contains it. */
export function searchLakes(index: SearchIndex, query: string, limit = 8): SearchResult {
  const q = fold(query.trim());
  if (q.length < MIN_QUERY) return { hits: [], total: 0 };

  const scored: (SearchHit & { score: number })[] = [];
  for (const row of index) {
    let score = 0;
    if (row.name.startsWith(q)) score = 4;
    else if (row.name.includes(` ${q}`)) score = 3;
    else if (row.name.includes(q) || row.kannada.includes(q)) score = 2;
    else if (row.ward.includes(q)) score = 1;
    if (score) scored.push({ lake: row.lake, byWard: score === 1, score });
  }

  scored.sort((a, b) => b.score - a.score || (b.lake.acres ?? 0) - (a.lake.acres ?? 0));
  return {
    hits: scored.slice(0, limit).map(({ lake, byWard }) => ({ lake, byWard })),
    total: scored.length,
  };
}
