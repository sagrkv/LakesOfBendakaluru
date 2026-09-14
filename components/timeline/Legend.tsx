import { formatCount } from "@/lib/format";
import Piece from "./Piece";
import type { Status } from "./types";
import { STATUSES } from "./words";

/** How each mark is made, with how many records are in each state. */
export default function Legend({ counts }: { counts: Record<Status, number> }) {
  return (
    <ul className="flex flex-wrap gap-x-6 gap-y-2">
      {STATUSES.map(({ status, name }) => (
        <li key={status} className="flex items-center gap-2 label font-normal">
          <Piece status={status} className="w-3! h-5! shrink-0" />
          <span>
            {name} <span className="text-missing tabular-nums">{formatCount(counts[status])}</span>
          </span>
        </li>
      ))}
    </ul>
  );
}
