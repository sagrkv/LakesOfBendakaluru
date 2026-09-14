import type { LakeRecord, Source, WaterClass } from "@/lib/lake";
import { formatAcres, formatMonth, WATER_CLASS } from "@/lib/format";
import { NOW } from "@/components/timeline/gaps";
import { resolve, sourcesOf } from "../sources";
import { joinList, percent } from "../words";
import { yearSpan, type Entry } from "./types";

const SURVEY = "the 2018 lake survey";

function point(id: string, year: number, label: string, sources: Source[], notes: string[] = []): Entry {
  return { id, from: year, when: String(year), label, notes, sources, lane: "records", tone: "lake" };
}

function builtEntries(lake: LakeRecord): Entry[] {
  const h = lake.history;
  const entries: Entry[] = [];
  // The survey has a few impossible years (a restoration in -2014); those are left off the line.
  if (h?.yearBuilt !== undefined && h.yearBuilt >= 1500 && h.yearBuilt <= 2018) {
    entries.push(point("built", h.yearBuilt, "Built", sourcesOf(h, "yearBuilt"), [`As ${SURVEY} records it`]));
  }
  if (h?.yearRejuvenated !== undefined && h.yearRejuvenated >= 1900 && h.yearRejuvenated <= NOW) {
    entries.push(point("restored", h.yearRejuvenated, "Restored", sourcesOf(h, "yearRejuvenated", "rejuvenated")));
  }
  return entries;
}

function surveyEntry(lake: LakeRecord): Entry[] {
  const h = lake.history;
  const e = lake.encroachment;
  const byEmpri = lake.src.status === "empri-2018";
  const facts = Boolean(
    byEmpri || lake.size?.surveyed2018Acres !== undefined || lake.water?.conditionIn2018?.length || e?.pct2018 !== undefined,
  );
  if (!facts && h?.goneBy === undefined) return [];

  const gone = lake.status !== "exists";
  const year = gone && h?.goneBy !== undefined ? h.goneBy : 2018;
  const label =
    gone && h?.goneBy !== undefined
      ? `Gone by ${h.goneBy}, says ${SURVEY}`
      : gone && byEmpri
        ? `Recorded as gone in ${SURVEY}`
        : !gone && byEmpri
          ? `Still there in ${SURVEY}`
          : `In ${SURVEY}`;

  const found = [
    e?.pct2018 !== undefined ? `${percent(e.pct2018)} encroached` : "",
    lake.water?.conditionIn2018?.length ? joinList(lake.water.conditionIn2018) : "",
    lake.size?.surveyed2018Acres !== undefined ? `${formatAcres(lake.size.surveyed2018Acres)} acres surveyed` : "",
  ].filter(Boolean);
  const notes = found.length ? [found.join(", ").replace(/^./, (c) => c.toUpperCase())] : [];
  const restoredYear = h?.yearRejuvenated !== undefined && h.yearRejuvenated >= 1900;
  if (h?.rejuvenated !== undefined && !restoredYear) notes.push(h.rejuvenated ? "Restored, year not recorded" : "Not restored");

  return [
    {
      id: "survey-2018",
      from: year,
      when: String(year),
      label,
      notes,
      sources: resolve([
        ...(byEmpri ? ["empri-2018"] : []),
        ...sourcesOf(h, "goneBy").map((s) => s.key),
        ...sourcesOf(e, "pct2018").map((s) => s.key),
        ...sourcesOf(lake.size, "surveyed2018Acres").map((s) => s.key),
        ...sourcesOf(lake.water, "conditionIn2018").map((s) => s.key),
      ]),
      lane: "records",
      tone: gone ? "no-lake" : "lake",
    },
  ];
}

function censusEntry(lake: LakeRecord): Entry[] {
  const e = lake.encroachment;
  if (e?.census2018Encroached === undefined) return [];
  return [
    {
      id: "census-2017",
      from: 2017,
      to: 2018,
      when: yearSpan(2017, 2018),
      label: e.census2018Encroached
        ? "Marked as encroached in the water bodies census"
        : "In the water bodies census, not marked as encroached",
      notes: ["This census's status marks are often wrong"],
      sources: sourcesOf(e, "census2018Encroached"),
      lane: "records",
      tone: "lake",
    },
  ];
}

function listEntry(lake: LakeRecord): Entry[] {
  const r = lake.responsibility;
  if (!r?.custodian || r.src.custodian !== "ktcda-lakes-2024") return [];
  return [point("list-2024", 2024, `On the state's list of Bengaluru lakes, looked after by ${r.custodian.code}`, sourcesOf(r, "custodian"))];
}

function testsEntry(lake: LakeRecord): Entry[] {
  const series = lake.waterQuality?.series ?? [];
  if (!series.length) return [];
  const months = [...new Set(series.map((r) => r.month))].sort();
  const counts = new Map<WaterClass, number>();
  for (const reading of series) if (reading.class) counts.set(reading.class, (counts.get(reading.class) ?? 0) + 1);
  const common = [...counts].sort((a, b) => b[1] - a[1] || b[0].localeCompare(a[0]))[0]?.[0];
  const from = Number(months[0].slice(0, 4));
  const to = Number(months[months.length - 1].slice(0, 4));
  const latest = [...series].sort((a, b) => b.month.localeCompare(a.month))[0];
  return [
    {
      id: "tests",
      from,
      to,
      when: yearSpan(from, to),
      label: `Tested by the state board in ${months.length} month${months.length === 1 ? "" : "s"}${
        common ? `, most often ${WATER_CLASS[common].short.toLowerCase()}` : ""
      }`,
      notes: [`${formatMonth(months[0])} to ${formatMonth(months[months.length - 1])}`],
      sources: resolve([latest.source]),
      lane: "records",
      tone: "lake",
      link: { href: "#water-quality", label: "See every test" },
    },
  ];
}

export function recordEntries(lake: LakeRecord): Entry[] {
  return [...builtEntries(lake), ...surveyEntry(lake), ...censusEntry(lake), ...listEntry(lake), ...testsEntry(lake)];
}
