import { formatCount } from "@/lib/format";
import type { Kind } from "./types";
import { KINDS } from "./words";

/** The paper each kind of record is cut from, with how many there are. */
export default function KindKey({ counts }: { counts: Record<Kind, number> }) {
  return (
    <ul className="flex flex-wrap gap-x-6 gap-y-2">
      {KINDS.map(({ kind, name, paper }) => (
        <li key={kind} className="label flex items-center gap-2 font-normal">
          <span aria-hidden className="size-[18px] shrink-0 rotate-12 border-2 border-ink" style={{ background: paper }} />
          <span>
            {name} <span className="text-missing tabular-nums">{formatCount(counts[kind])}</span>
          </span>
        </li>
      ))}
    </ul>
  );
}
