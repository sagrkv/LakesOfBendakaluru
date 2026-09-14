import Link from "next/link";
import { formatAcres } from "@/lib/format";
import { sentence } from "@/components/lake/words";
import type { Tagged } from "./filter";
import { whenLine } from "./when";
import { whoLine } from "./who";

export const ROW = "-mx-2 px-2 grid-cols-12 gap-x-6 items-baseline";
const SMALL = "label font-normal md:text-[17px] md:leading-[1.55]";

/** One past lake: its name and size, when it went, and why, as far as the record says. */
export default function PastRow({ lake, printed }: { lake: Tagged; printed?: number[] }) {
  const when = whenLine(lake, printed);
  const filledIn = whoLine(lake.convertedBy);

  return (
    <li className="border-b border-rule [content-visibility:auto] [contain-intrinsic-size:auto_96px] md:[contain-intrinsic-size:auto_80px]">
      <Link
        href={`/lake/${lake.id}`}
        prefetch={false}
        className={`${ROW} grid group gap-y-1 py-3 hover:bg-well active:bg-rule`}
      >
        <span className="col-span-8 md:col-span-3 underline decoration-1 underline-offset-3 group-hover:decoration-2">
          {lake.name}
        </span>
        <span className="col-span-4 md:col-span-2 text-right tabular-nums">
          {lake.acres ? (
            <>
              {formatAcres(lake.acres)}
              <span className="md:sr-only"> acres</span>
            </>
          ) : (
            <span className="missing">not recorded</span>
          )}
        </span>
        <span className={`col-span-12 md:col-span-3 ${SMALL}`}>
          <span className="sr-only">When it went: </span>
          {when ?? <span className="missing">Nothing on record dates it</span>}
        </span>
        <span className={`col-span-12 md:col-span-4 ${SMALL}`}>
          <span className="sr-only">Why: </span>
          {lake.nowOccupiedBy || filledIn ? (
            <>
              {lake.nowOccupiedBy && <span className="block">{sentence(lake.nowOccupiedBy)}</span>}
              {filledIn && <span className={`block label font-normal ${lake.nowOccupiedBy ? "mt-1" : ""}`}>{filledIn}</span>}
            </>
          ) : (
            <span className="missing">No reason on record</span>
          )}
        </span>
      </Link>
    </li>
  );
}
