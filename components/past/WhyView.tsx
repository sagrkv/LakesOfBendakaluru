import type { ReactNode } from "react";
import BarGroup, { type Bar } from "./BarGroup";
import type { Counts } from "./filter";
import { OCCUPIED, type OccupiedId } from "./occupied";
import ViewSection from "./ViewSection";
import { WHO, type WhoId } from "./who";

const CLOSING = new Set(["other", "none"]);

/** Largest first; "something else" and "not on record" always close the list. */
function barsOf<Id extends string>(groups: { id: Id; label: string }[], counts: Partial<Record<Id, number>>): Bar[] {
  return groups
    .map((group) => ({ id: group.id, label: group.label, count: counts[group.id] ?? 0, missing: group.id === "none" }))
    .filter((bar) => bar.count > 0)
    .sort((a, b) => Number(CLOSING.has(a.id)) - Number(CLOSING.has(b.id)) || b.count - a.count);
}

/** What the record gives as the reason: what stands on the site, and who filled it in. */
export default function WhyView({
  counts,
  now,
  who,
  onPickNow,
  onPickWho,
  children,
}: {
  counts: Counts;
  now: OccupiedId | null;
  who: WhoId | null;
  onPickNow: (id: OccupiedId | null) => void;
  onPickWho: (id: WhoId | null) => void;
  children: ReactNode;
}) {
  const nowBars = barsOf(OCCUPIED, counts.now);
  const whoBars = barsOf(WHO, counts.who);
  const max = Math.max(...nowBars.map((bar) => bar.count), ...whoBars.map((bar) => bar.count));

  return (
    <ViewSection
      id="why"
      title="Why they went"
      note={
        <>
          <p>
            The 2018 lake survey noted what stands on each site and who filled it in. Lakes known only from old maps
            have no reason on record.
          </p>
          <p>Some sites name more than one party, so the second list adds up to more. Choose a bar to list only those lakes.</p>
        </>
      }
    >
      <BarGroup
        title="On the site now"
        bars={nowBars}
        max={max}
        picked={now}
        onPick={(id) => onPickNow(id as OccupiedId | null)}
      />
      <BarGroup
        title="Filled in by"
        bars={whoBars}
        max={max}
        picked={who}
        onPick={(id) => onPickWho(id as WhoId | null)}
        showTotal={false}
      />
      {children}
    </ViewSection>
  );
}
