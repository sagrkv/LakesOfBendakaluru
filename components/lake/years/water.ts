import type { LakeRecord, LandCoverYear, Source } from "@/lib/lake";
import { resolve, sourcesOf } from "../sources";
import { percent, sentence } from "../words";
import { yearSpan, type Entry, type Season } from "./types";

type Water = LakeRecord["water"];
type Year = NonNullable<NonNullable<Water>["yearly"]>[number];

/** A year the satellite saw less than half of the lake's usual area; its low reading is not real. */
export function poorYear(year: Year, maxObserved: number): boolean {
  return year.observedAcres < maxObserved * 0.5;
}

export function maxObservedOf(years: Year[]): number {
  return Math.max(0, ...years.map((y) => y.observedAcres));
}

/** Several yearly releases share one page; one link is enough. */
function byAddress(sources: Source[]): Source[] {
  const seen = new Map<string, Source>();
  for (const source of sources) seen.set(source.url ?? source.key, source);
  return [...seen.values()];
}

function yearlyEntry(water: Water, lastSeen: number | undefined): Entry[] {
  const years = water?.yearly ?? [];
  const maxObserved = maxObservedOf(years);
  if (!years.length || maxObserved <= 0) return lastSeenEntry(lastSeen);

  const first = years[0].year;
  const last = years[years.length - 1].year;
  const good = years.filter((y) => !poorYear(y, maxObserved));
  const wet = good.filter((y) => y.waterAcres > 0);
  const lastWet = wet.length ? wet[wet.length - 1].year : undefined;

  const label =
    lastWet === undefined
      ? "No open water seen in any year"
      : lastWet <= last - 3
        ? `Held water until ${lastWet}`
        : wet.length === good.length
          ? "Held water every year"
          : wet.length >= (good.length * 2) / 3
            ? "Held water most years"
            : `Held water in ${wet.length} of ${good.length} years`;

  const presence = water?.presence;
  const notes: string[] = [];
  if (presence && presence.occurrencePct > 0) {
    notes.push(`Water in ${percent(presence.occurrencePct)} of all satellite passes, 1984-2024`);
  }
  if (presence && (presence.lostPct > 0 || presence.gainedPct > 0)) {
    notes.push(`${percent(presence.lostPct)} of its water area has since gone dry; ${percent(presence.gainedPct)} is new water`);
  }
  const poorCount = years.length - good.length;
  if (poorCount > 0) {
    notes.push(`${poorCount} year${poorCount === 1 ? "" : "s"} not counted: the satellite saw under half the lake`);
  }
  const weedy = (water?.current ?? []).some((c) => c.weedCoverPct >= 20 && !c.lowConfidence);
  if (weedy && !presence?.lowConfidence) {
    notes.push("Floating weed looks like dry land to this record, so a weed-covered year can read as dry");
  }
  if (presence?.lowConfidence) notes.push("The lake is small for this record, so treat it as rough");

  const entry: Entry = {
    id: "water-yearly",
    from: first,
    to: last,
    when: yearSpan(first, last),
    label,
    notes,
    sources: sourcesOf(water, "yearly", "presence"),
    lane: "water",
    tone: wet.length ? "lake" : "no-lake",
  };
  // The strip already shows the last wet year; a later sighting from the newer summary is its own fact.
  return lastSeen !== undefined && (lastWet === undefined || lastSeen > last) ? [entry, ...lastSeenEntry(lastSeen)] : [entry];
}

function lastSeenEntry(year: number | undefined): Entry[] {
  if (year === undefined) return [];
  return [
    {
      id: "last-seen",
      from: year,
      when: String(year),
      label: "Last seen with water by satellite",
      notes: [],
      sources: resolve(["jrc-gsw-1-5"]),
      lane: "records",
      tone: "lake",
    },
  ];
}

type Shares = { water: number; plants: number; built: number };

export function sharesOf(row: LandCoverYear): Shares {
  return {
    water: row.waterPct,
    plants: row.floodedVegetationPct + row.treesPct + row.cropsPct + row.rangelandPct,
    built: row.builtPct + row.bareGroundPct,
  };
}

const COVER_WORDS: Record<keyof Shares, string> = {
  water: "water",
  plants: "plants or weed",
  built: "built on or bare",
};

function coverLabel(rows: LandCoverYear[]): { label: string; majority?: keyof Shares } {
  const shares = rows.map(sharesOf);
  const most = (key: keyof Shares) => shares.filter((s) => s[key] >= 50).length;

  const builtFrom = shares.findIndex((_, i) => shares.slice(i).every((s) => s.built >= 50));
  if (builtFrom !== -1 && rows.length - builtFrom >= 3) {
    return {
      label: builtFrom === 0 ? "Mostly built on or bare every year" : `Mostly built on or bare from ${rows[builtFrom].year}`,
      majority: "built",
    };
  }
  for (const key of ["water", "plants", "built"] as const) {
    if (most(key) === rows.length) return { label: `Mostly ${COVER_WORDS[key]} every year`, majority: key };
    if (most(key) >= (rows.length * 2) / 3) return { label: `Mostly ${COVER_WORDS[key]} in most years`, majority: key };
  }
  return { label: "No one cover holds over half of it in most years" };
}

function coverEntry(lake: LakeRecord): Entry[] {
  const rows = [...(lake.water?.landCoverYearly ?? [])].sort((a, b) => a.year - b.year);
  if (!rows.length) return [];
  const { label, majority } = coverLabel(rows);
  const notes: string[] = [];
  const rough = rows.some((r) => r.lowConfidence);
  if (majority === "plants" && lake.status === "exists" && !rough) {
    notes.push("Floating weed shows as crops or grass here, not as water");
  }
  if (rough) {
    notes.push("The lake is known only as a point or is under a quarter acre, so the shares are rough");
  }
  notes.push("About three in four of these readings are right, so trust what holds for several years");
  const first = rows[0].year;
  const last = rows[rows.length - 1].year;
  return [
    {
      id: "land-cover",
      from: first,
      to: last,
      when: yearSpan(first, last),
      label,
      notes,
      // Every release shares one page; keep the newest year's citation for it.
      sources: byAddress(resolve(rows.map((r) => r.source))),
      lane: "cover",
      tone: majority === "built" ? "no-lake" : "lake",
    },
  ];
}

const SEASON_PHRASE: Record<string, string> = { "after monsoon": "after the monsoon", "dry season": "in the dry season" };
const PARTS = [
  ["openWaterPct", "open water"],
  ["weedCoverPct", "floating weed"],
  ["dryOrBuiltPct", "dry or built"],
] as const;

function seasonWords(season: Season): string {
  const ranked = [...PARTS].sort((a, b) => season[b[0]] - season[a[0]]);
  return season[ranked[0][0]] >= 50 ? `mostly ${ranked[0][1]}` : `part ${ranked[0][1]}, part ${ranked[1][1]}`;
}

function currentEntry(water: Water): Entry[] {
  const seasons = water?.current ?? [];
  if (!seasons.length) return [];
  const from = Math.min(...seasons.map((s) => Number(s.from.slice(0, 4))));
  const to = Math.max(...seasons.map((s) => Number(s.to.slice(0, 4))));
  const words = seasons.map(seasonWords);
  const phrases = seasons.map((s) => SEASON_PHRASE[s.season] ?? `in the ${s.season}`);
  const label =
    words.every((w) => w === words[0]) && seasons.length > 1
      ? `${sentence(words[0])} ${phrases.join(" and ")}`
      : sentence(words.map((w, i) => `${w} ${phrases[i]}`).join("; "));
  return [
    {
      id: "current",
      from,
      to,
      when: yearSpan(from, to),
      label,
      notes: seasons.some((s) => s.lowConfidence) ? ["The lake is small for these images, so treat the shares as rough"] : [],
      sources: byAddress(resolve(seasons.map((s) => s.source))),
      lane: "records",
      tone: seasons.some((s) => s.openWaterPct >= 10) ? "lake" : "no-lake",
      seasons,
    },
  ];
}

export function waterEntries(lake: LakeRecord): Entry[] {
  return [...yearlyEntry(lake.water, lake.history?.lastSeenWithWater), ...coverEntry(lake), ...currentEntry(lake.water)];
}
