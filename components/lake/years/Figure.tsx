import type { CSSProperties } from "react";
import type { LakeRecord } from "@/lib/lake";
import { tiltFor } from "@/components/paper/Slip";
import { columnsOf, GAP_CAP, type Segment } from "./axis";
import CoverLane from "./CoverLane";
import Piece from "./Piece";
import RecordsLane from "./RecordsLane";
import Ticks from "./Ticks";
import type { Entry } from "./types";
import WaterLane from "./WaterLane";

/**
 * Every record on one line, from the oldest to today, pasted on a cream slip.
 * Visual only: the list under it says the same, with sources.
 */
export default function Figure({ lake, entries, segments }: { lake: LakeRecord; entries: Entry[]; segments: Segment[] }) {
  const records = entries.filter((entry) => entry.lane === "records");
  const years = entries.some((entry) => entry.lane === "water") ? (lake.water?.yearly ?? []) : [];
  const cover = entries.some((entry) => entry.lane === "cover")
    ? [...(lake.water?.landCoverYearly ?? [])].sort((a, b) => a.year - b.year)
    : [];
  const style = {
    "--tilt": `${tiltFor(`${lake.id}-years`) * 0.2}deg`,
    "--cols": columnsOf(segments, GAP_CAP.phone),
    "--cols-wide": columnsOf(segments, GAP_CAP.wide),
  } as CSSProperties;

  return (
    <figure className="slip min-w-0 px-4 pt-4 pb-3 md:px-6 md:pt-6 md:pb-4" style={style}>
      <figcaption className="sr-only">
        The records listed below, drawn on one line from {segments[0]?.from} to {segments[segments.length - 1]?.to}.
      </figcaption>
      {records.length ? (
        <ul aria-hidden className="label flex flex-wrap gap-x-6 gap-y-2 font-normal">
          <li className="flex items-center gap-2">
            <Piece tone="lake" className="h-3.5 w-1.5 shrink-0" />
            The record shows a lake
          </li>
          {records.some((entry) => entry.tone === "no-lake") ? (
            <li className="flex items-center gap-2">
              <Piece tone="no-lake" className="h-3.5 w-1.5 shrink-0" />
              The record shows no lake
            </li>
          ) : null}
        </ul>
      ) : null}

      <div aria-hidden className={`grid grid-cols-(--cols) md:grid-cols-(--cols-wide) ${records.length ? "mt-10" : "mt-4"}`}>
        {records.length ? <RecordsLane entries={records} segments={segments} /> : null}
        {years.length ? <WaterLane years={years} segments={segments} /> : null}
        {cover.length ? <CoverLane rows={cover} segments={segments} /> : null}
        <Ticks segments={segments} />
      </div>
    </figure>
  );
}
