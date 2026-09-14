"use client";

import { useMemo, useState, type ReactNode } from "react";
import { matches, NO_FILTER, tag, type Counts, type Filter } from "./filter";
import ListSection from "./ListSection";
import MatchLine from "./MatchLine";
import RecordView from "./RecordView";
import type { MissingLake } from "./types";
import { useAllMissing } from "./useAllMissing";

/** The bars and the list below them share one set of choices. */
export default function Explorer({
  top,
  counts,
  total,
  note,
}: {
  top: MissingLake[];
  counts: Counts;
  total: number;
  note: ReactNode;
}) {
  const [filter, setFilter] = useState<Filter>(NO_FILTER);
  const all = useAllMissing();
  const topTagged = useMemo(() => top.map(tag), [top]);
  const rows = useMemo(() => all.lakes?.filter((lake) => matches(lake, filter)) ?? null, [all.lakes, filter]);

  const pick = (next: Partial<Filter>) => {
    setFilter((current) => ({ ...current, ...next }));
    void all.load();
  };

  return (
    <>
      <RecordView counts={counts} filter={filter} note={note} onPick={pick}>
        <MatchLine filter={filter} count={rows?.length ?? null} failed={all.status === "error"} />
      </RecordView>
      <ListSection
        filter={filter}
        top={topTagged}
        all={all}
        rows={rows}
        total={total}
        onLoad={() => void all.load()}
        onClear={() => setFilter(NO_FILTER)}
      />
    </>
  );
}
