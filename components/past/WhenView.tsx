import Link from "next/link";
import type { ReactNode } from "react";
import BarGroup, { type Bar } from "./BarGroup";
import type { Counts } from "./filter";
import ViewSection from "./ViewSection";
import { parseWhen, WHEN_GROUPS, whenLabel, type WhenKind } from "./when";

function barsOf(counts: Counts, kind: WhenKind): Bar[] {
  return Object.entries(counts.when)
    .map(([id, count]) => ({ when: parseWhen(id), count }))
    .filter(({ when }) => when.kind === kind)
    .sort((a, b) => (a.when.year ?? 0) - (b.when.year ?? 0))
    .map(({ when, count }) => ({ id: when.id, label: whenLabel(when), count, missing: kind === "none" }));
}

/** Counts by the best dated evidence, oldest evidence first, all on one scale. */
export default function WhenView({
  counts,
  picked,
  onPick,
  children,
}: {
  counts: Counts;
  picked: string | null;
  onPick: (id: string | null) => void;
  children: ReactNode;
}) {
  const max = Math.max(...Object.values(counts.when));
  const [map, satellite, survey, none] = WHEN_GROUPS.map((group) => (
    <BarGroup key={group.kind} title={group.title} bars={barsOf(counts, group.kind)} max={max} picked={picked} onPick={onPick} />
  ));

  return (
    <ViewSection
      id="when"
      title="When they went"
      note={
        <>
          <p>
            Each lake is dated by the best evidence on record. The 2018 lake survey says which year it was gone by.
            Satellites have watched for water since 1984. Survey maps printed from 1914 to 1980 show water where there is
            none today.
          </p>
          <p>
            Choose a bar to list only those lakes. <Link href="/sources" className="ink-link">See the sources</Link>
          </p>
        </>
      }
    >
      <div className="grid gap-y-10 content-start">
        {map}
        {satellite}
      </div>
      <div className="grid gap-y-10 content-start">
        {survey}
        {none}
      </div>
      {children}
    </ViewSection>
  );
}
