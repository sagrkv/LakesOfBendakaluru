/**
 * What stands on a lost lake's site now, grouped into plain categories.
 * The 2018 inventory writes it as free text ("Vacant land & houses"); the first thing named decides the group.
 * No imports, so it runs in the browser and in a plain node check.
 */

export type OccupiedId =
  | "empty"
  | "farms"
  | "homes"
  | "buildings"
  | "roads"
  | "campuses"
  | "institutions"
  | "parks"
  | "other"
  | "none";

/** `phrase` finishes "Showing the 225 lakes ...". */
export type Occupied = { id: OccupiedId; label: string; phrase: string };

export const OCCUPIED: Occupied[] = [
  { id: "empty", label: "Empty land and dumps", phrase: "that are now empty land or dumps" },
  { id: "farms", label: "Farms and plantations", phrase: "that are now farms or plantations" },
  { id: "homes", label: "Houses and layouts", phrase: "that are now houses or layouts" },
  { id: "buildings", label: "Buildings, sheds and business parks", phrase: "that are now buildings, sheds or business parks" },
  { id: "roads", label: "Roads, rail and bus depots", phrase: "that are now roads, rail or bus depots" },
  { id: "campuses", label: "Defence and government campuses", phrase: "that are now defence or government campuses" },
  { id: "institutions", label: "Schools, temples, hospitals and graveyards", phrase: "that are now schools, temples, hospitals or graveyards" },
  { id: "parks", label: "Parks, grounds and trees", phrase: "that are now parks, grounds or trees" },
  { id: "other", label: "Something else", phrase: "that are now something else" },
  { id: "none", label: "Not on record", phrase: "with nothing on record about the site" },
];

type Named = Exclude<OccupiedId, "other" | "none">;

/** Checked in this order, so "HAL airport" is a campus and "Golf business park" is a building. */
const RULES: [Named, RegExp][] = [
  ["campuses", /\b(HAL|ISRO|CRPF|DRDO|BEL)\b|air ?force|military|army|defen[cs]e|aeronautical|aerospace|telephone indust|university|cantonm|police|jail/i],
  ["institutions", /school|college|coll\.|temple|masjid|mosque|church|hospital|graveyard|burial|cemetery|crematori|samud(h)?aya|art of living|institute|inst\.|gurukula|research|laborat|library|anganawadi|hostel|pathasala|\blab\b/i],
  ["homes", /house|layout|settlement|apartment|villa|quarters|colony|slum|residential|residency|housing|flats/i],
  ["buildings", /building|godown|shed|shelter|business park|te(c|ck) park|industr|commercial|factory|shops?\b|office|choultr|warehouse|\bbank\b|\bltd\b|company|software|mot(o|a)rs|logistic|\bmall\b|consultancy|\bDHL\b|works?\b|manuf|marble|granite|petrol|mantapa|club|market|bhavan|tower|garage|workshop|dhaba|\btank\b|tech mahindra/i],
  ["roads", /\broads?\b|\brd\b|railway|metro|\bbus\b|BMTC|KSRTC|airport|highway/i],
  ["farms", /agricultur|plantai?tion|eucal|eycu|farm|nursery|\bcrops?\b|orchard/i],
  ["empty", /vacan|bare land|open (ground|land)|barren|dump|waste/i],
  ["parks", /park|ground|stadium|\btrees?\b|forest|golf|garden|pool/i],
];

function match(text: string): Named | undefined {
  return RULES.find(([, pattern]) => pattern.test(text))?.[0];
}

export function occupiedId(nowOccupiedBy: string | undefined): OccupiedId {
  const text = nowOccupiedBy?.trim();
  if (!text) return "none";
  const first = text.split(/[,&/(]| and /)[0];
  return match(first) ?? match(text) ?? "other";
}
