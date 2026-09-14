import type { CSSProperties, ReactNode } from "react";
import Slip, { tiltFor } from "@/components/paper/Slip";
import type { LakeRecord, LakeSummary } from "@/lib/lake";
import { WATER_CLASS, formatAcres, formatCount, formatMonth, ordinal, pitches } from "@/lib/format";
import type { Paper } from "@/lib/valleys";
import { serifEm } from "./fit";
import type { Opener } from "./opener";
import WhereSlip from "./WhereSlip";

type Fact = { key: string; label: ReactNode; value?: string; note?: string; missing: string };

/** Inner width of a slip in a two-column grid on a 360 px phone, where values are 26 px. */
const PHONE_SLIP_INNER = 124;

const capitalise = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);

function percent(n: number): string {
  if (n >= 10) return `${Math.round(n)}%`;
  return `${Number.isInteger(n) ? n : n.toFixed(1)}%`;
}

function facts(lake: LakeRecord, summary: LakeSummary, paper: Paper, ranked: number): Fact[] {
  const acres = summary.acres ?? lake.size?.outlineAcres;
  const rank = summary.sizeRank;
  const valley = summary.valley ?? lake.water?.valley;
  const custodian = lake.responsibility?.custodian;
  const built = summary.builtPct ?? lake.nature?.builtInsideOutlinePct;
  const waterClass = summary.waterClass;

  return [
    {
      key: "size",
      label: "Size",
      value: acres === undefined ? undefined : `${formatAcres(acres)} acres`,
      note: acres === undefined ? undefined : capitalise(pitches(acres).startsWith("smaller") ? pitches(acres) : `about ${pitches(acres)}`),
      missing: "Not measured yet",
    },
    {
      key: "rank",
      label: "Rank by size",
      value: rank === undefined ? undefined : rank === 1 ? "The largest" : `${ordinal(rank)} largest`,
      note: rank === undefined ? undefined : `Of ${formatCount(ranked)} lakes that still exist`,
      missing: "Not ranked yet",
    },
    {
      key: "valley",
      label: (
        <span className="inline-flex items-center gap-2">
          <span aria-hidden="true" className="size-3 shrink-0" style={{ background: paper.sheet }} />
          Valley
        </span>
      ),
      value: valley,
      missing: "No valley on record",
    },
    {
      key: "custodian",
      label: "Looks after it",
      value: custodian ? custodian.code : undefined,
      note: custodian && custodian.name !== custodian.code ? custodian.name : undefined,
      missing: "Nobody on record looks after it",
    },
    {
      key: "water",
      label: "Water quality",
      value: waterClass ? WATER_CLASS[waterClass].short : undefined,
      note: summary.waterClassMonth ? `Tested ${formatMonth(summary.waterClassMonth)}` : undefined,
      missing: "Not tested for water quality yet",
    },
    {
      key: "built",
      label: "Built over",
      value: built === undefined ? undefined : percent(built),
      note: built === undefined ? undefined : "Buildings inside its outline, 2021",
      missing: "Not measured yet",
    },
  ];
}

/** A phone slip takes the full row when one of its words is wider than a half-width slip. */
function needsFullRow(text: string): boolean {
  return text.split(/[\s-]+/).some((word) => serifEm(word) * 26 > PHONE_SLIP_INNER);
}

/** The stamp, six fact slips and the where slip, pasted in that order after the sheet lands. */
export default function Facts({ opener, paper, className = "" }: { opener: Opener; paper: Paper; className?: string }) {
  const { lake, summary, city } = opener;
  const list = facts(lake, summary, paper, city.ranked);
  const stampStyle = { "--tilt": `${tiltFor(`${lake.id}-stamp`)}deg`, "--delay": "600ms" } as CSSProperties;

  return (
    <div className={className}>
      {summary.campaign ? (
        <p
          className="slip pastes mb-6 inline-block px-6 pt-4 pb-4.5 font-serif italic text-[26px] leading-none outline-2 -outline-offset-8 outline-ink md:text-[36px]"
          style={stampStyle}
        >
          Residents are organising here
        </p>
      ) : null}
      <div className="grid grid-flow-dense grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-2">
        {list.map((fact, i) => (
          <Slip
            key={fact.key}
            seed={`${lake.id}-${fact.key}`}
            label={fact.label}
            order={i + 1}
            className={needsFullRow(fact.value ?? fact.missing) ? "col-span-2 md:col-span-1" : ""}
          >
            {fact.value ? (
              <>
                {fact.value}
                {fact.note ? <span className="label mt-2 block font-sans">{fact.note}</span> : null}
              </>
            ) : (
              <span className="missing">{fact.missing}</span>
            )}
          </Slip>
        ))}
        <WhereSlip
          lake={lake}
          sheet={lake.sheet}
          xy={summary.xy}
          city={city}
          sheetColor={paper.sheet}
          order={list.length + 1}
          className="col-span-full"
        />
      </div>
    </div>
  );
}
