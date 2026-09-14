/** Plain words for the codes and lists in a lake record. */

/** Inventory names that were never given a proper name arrive as slugs. */
export function displayName(name: string): string {
  if (!/^[a-z0-9-]+$/.test(name)) return name;
  return name
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

/** "a", "a and b", "a, b and c". */
export function joinList(items: string[]): string {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}

export function sentence(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function percent(n: number): string {
  if (n === 0) return "0%";
  if (n < 1) return `${n.toFixed(1)}%`;
  return `${Math.round(n)}%`;
}

const DIRECTIONS: Record<string, string> = {
  N: "north",
  NE: "north-east",
  E: "east",
  SE: "south-east",
  S: "south",
  SW: "south-west",
  W: "west",
  NW: "north-west",
};

/** "N;NW" or ["N", "W"] to "north and north-west". Unknown codes are kept as written. */
export function directions(codes: string | string[]): string {
  const list = Array.isArray(codes) ? codes : codes.split(/[;,\s]+/);
  return joinList(list.filter(Boolean).map((code) => DIRECTIONS[code.toUpperCase()] ?? code));
}

const WHO: Record<string, string> = {
  government: "government agencies",
  public: "the public",
  private: "private owners",
  farmers: "farmers",
};

export function who(list: string[]): string {
  return joinList(list.map((w) => WHO[w] ?? w));
}

const KIND: Record<string, string> = {
  kere: "Kere, a large tank",
  katte: "Katte, a medium tank",
  kunte: "Kunte, a small pond",
};

export function kindWords(kind: string): string {
  return KIND[kind] ?? kind;
}

const IUCN: Record<string, string> = {
  NT: "Near threatened",
  VU: "Vulnerable",
  EN: "Endangered",
  CR: "Critically endangered",
};

export function iucnWords(code: string): string {
  return IUCN[code] ?? code;
}

/** GBIF writes "Milvus migrans (Black Kite)"; people know the bird as a black kite. */
export function commonName(species: string): string {
  const match = species.match(/\(([^)]+)\)\s*$/);
  return match ? match[1] : species;
}

export function hostname(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

/** "2025-10-01" to "Oct 2025". */
export function monthOf(date: string): string {
  const [y, m] = date.split("-");
  const names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return m ? `${names[Number(m) - 1]} ${y}` : y;
}
