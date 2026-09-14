import type { ReactNode } from "react";
import BarGroup, { type Bar } from "@/components/past/BarGroup";
import ViewSection from "@/components/past/ViewSection";
import { NEWER, NO_TALUK, SIZES, type Counts, type Filter, type NewerId, type SizeId } from "./filter";

function talukBars(counts: Counts): Bar[] {
  return Object.entries(counts.taluk)
    .map(([id, count]) => ({ id, label: id === NO_TALUK ? "No taluk on record" : id, count, missing: id === NO_TALUK }))
    .sort((a, b) => Number(a.missing) - Number(b.missing) || b.count - a.count);
}

function groupBars<Id extends string>(groups: { id: Id; label: string }[], counts: Partial<Record<Id, number>>): Bar[] {
  return groups
    .map((group) => ({ id: group.id, label: group.label, count: counts[group.id] ?? 0, missing: group.id === "none" }))
    .filter((bar) => bar.count > 0);
}

/** Where the lakes are, how big the survey found them, and whether anything newer is on record, all on one scale. */
export default function RecordView({
  counts,
  filter,
  note,
  onPick,
  children,
}: {
  counts: Counts;
  filter: Filter;
  note: ReactNode;
  onPick: (next: Partial<Filter>) => void;
  children: ReactNode;
}) {
  const taluks = talukBars(counts);
  const sizes = groupBars(SIZES, counts.size);
  const newer = groupBars(NEWER, counts.newer);
  const max = Math.max(...[...taluks, ...sizes, ...newer].map((bar) => bar.count));

  return (
    <ViewSection id="record" title="Where they are, and how small" note={note}>
      <div className="grid gap-y-10 content-start">
        <BarGroup title="Taluk" bars={taluks} max={max} picked={filter.taluk} onPick={(taluk) => onPick({ taluk })} />
        <BarGroup
          title="Since the 2018 survey"
          bars={newer}
          max={max}
          picked={filter.newer}
          onPick={(id) => onPick({ newer: id as NewerId | null })}
        />
      </div>
      <BarGroup
        title="Size recorded in 2018"
        bars={sizes}
        max={max}
        picked={filter.size}
        onPick={(id) => onPick({ size: id as SizeId | null })}
      />
      {children}
    </ViewSection>
  );
}
