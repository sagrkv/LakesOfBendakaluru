import Link from "next/link";
import type { ReactNode } from "react";
import type { LakeSummary } from "@/lib/lake";
import CollectionPicker from "./CollectionPicker";
import GoneLink from "./GoneLink";
import type { CollectionKey } from "./collections";
import Legend from "./Legend";
import SearchBox from "./SearchBox";
import type { SearchIndex } from "./search";

type Props = {
  stats: string | null;
  gone: number | null;
  missing: number | null;
  index: SearchIndex | null;
  failed: boolean;
  counts: Partial<Record<CollectionKey, number>> | null;
  onChoose: (key: CollectionKey) => void;
  onPick: (lake: LakeSummary) => void;
  /** The open collection's list, or nothing to show the collections. */
  list: ReactNode;
};

/** The laptop layout: a fixed 400 px panel left of the map. */
export default function SidePanel({ stats, gone, missing, index, failed, counts, onChoose, onPick, list }: Props) {
  return (
    <aside className="flex h-full w-[400px] shrink-0 flex-col border-r border-rule bg-table">
      <div className="px-6 pt-6 pb-6">
        <Link href="/" className="font-serif text-[28px] leading-none italic">
          Lakes of Bendakaluru
        </Link>
        <p className={`label mt-2 text-missing ${stats ? "" : "invisible"}`}>
          {stats ?? "Counting the lakes"} <GoneLink gone={gone} missing={missing} />
        </p>
        <div className="mt-4">
          <SearchBox index={index} failed={failed} onPick={onPick} />
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col">
        {list ?? (
          <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
            <CollectionPicker variant="rows" counts={counts} disabled={!index} onChoose={onChoose} />
          </div>
        )}
      </div>

      <div className="border-t border-rule px-6 py-4">
        <Legend columns={2} />
      </div>
    </aside>
  );
}
