"use client";

import { useMemo, useState } from "react";
import { matches, NO_FILTER, tag, type Counts, type Filter } from "./filter";
import ListSection from "./ListSection";
import MatchLine from "./MatchLine";
import type { PastLake } from "./types";
import { useAllPast } from "./useAllPast";
import WhenView from "./WhenView";
import WhyView from "./WhyView";

/**
 * The when and why views and the list below them share one set of choices.
 * `printed` holds real map print years by lake id, for lakes on a map edition printed over several years.
 */
export default function Explorer({
  top,
  counts,
  total,
  printed,
}: {
  top: PastLake[];
  counts: Counts;
  total: number;
  printed: Record<string, number[]>;
}) {
  const [filter, setFilter] = useState<Filter>(NO_FILTER);
  const all = useAllPast();
  const topTagged = useMemo(() => top.map(tag), [top]);
  const rows = useMemo(() => all.lakes?.filter((lake) => matches(lake, filter)) ?? null, [all.lakes, filter]);

  const pick = (next: Partial<Filter>) => {
    setFilter((current) => ({ ...current, ...next }));
    void all.load();
  };
  const matchLine = <MatchLine filter={filter} count={rows?.length ?? null} failed={all.status === "error"} />;

  return (
    <>
      <WhenView counts={counts} picked={filter.when} onPick={(when) => pick({ when })}>
        {matchLine}
      </WhenView>
      <WhyView
        counts={counts}
        now={filter.now}
        who={filter.who}
        onPickNow={(now) => pick({ now })}
        onPickWho={(who) => pick({ who })}
      >
        {matchLine}
      </WhyView>
      <ListSection
        filter={filter}
        top={topTagged}
        all={all}
        rows={rows}
        total={total}
        printed={printed}
        onLoad={() => void all.load()}
        onClear={() => setFilter(NO_FILTER)}
      />
    </>
  );
}
