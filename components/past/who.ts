/**
 * Who filled a lake in, as the 2018 lake survey wrote it, grouped into plain parties.
 * The survey mixes kinds ("government") with names ("BDA", "Prestige Grp"); a lake can name several.
 */

import { who } from "@/components/lake/words";

export type WhoId = "private" | "government" | "public" | "farmers" | "none";
/** `phrase` finishes "Showing the 12 lakes ...". */
export type WhoGroup = { id: WhoId; label: string; phrase: string };

export const WHO: WhoGroup[] = [
  { id: "private", label: "Private owners and builders", phrase: "filled in by private owners or builders" },
  { id: "government", label: "Government agencies", phrase: "filled in by government agencies" },
  { id: "public", label: "The public", phrase: "filled in by the public" },
  { id: "farmers", label: "Farmers", phrase: "filled in by farmers" },
  { id: "none", label: "Nobody on record", phrase: "with nobody on record as filling them in" },
];

const UNKNOWN = /^(unknown|unkown)$/i;

/** Checked in this order, so "BEL Employees Co-operative Society" is private and "ITI Ltd" is government. */
const RULES: [Exclude<WhoId, "none">, RegExp][] = [
  ["private", /private|pvt|priv\.|develop|devaloper|builder|employees|society|apart/i],
  ["government", /government|govt|\b(BDA|BBMP|KHB|KFD|KSPCB|UAS|BEL|ITI|BSNL)\b|forest|horticulture|railway|army|air force|defence/i],
  ["public", /public|villagers/i],
  ["farmers", /farmer/i],
];

function named(list: string[] | undefined): string[] {
  return (list ?? []).map((name) => name.trim()).filter((name) => name && !UNKNOWN.test(name));
}

/** Named companies, colleges and trusts that match no rule are private. */
export function whoIds(list: string[] | undefined): WhoId[] {
  const ids = named(list).map((name) => RULES.find(([, pattern]) => pattern.test(name))?.[0] ?? "private");
  return ids.length ? [...new Set(ids)] : ["none"];
}

/** Survey spellings tidied for reading; the names stay as recorded. */
function tidy(name: string): string {
  return name.replace(/^inside /i, "").replace(/ofnursing/i, "of nursing").replace(/^devaloper$/i, "developers");
}

/** "Filled in by private owners and BDA"; null when nobody is on record. */
export function whoLine(list: string[] | undefined): string | null {
  const names = named(list).map(tidy);
  return names.length ? `Filled in by ${who(names)}` : null;
}
