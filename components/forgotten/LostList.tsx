import Link from "next/link";
import { formatAcres } from "@/lib/format";
import type { LostLake } from "./lost";

const ROW = "-mx-2 px-2 grid-cols-12 gap-x-6 items-baseline";

/** Every lost lake, one row each. Rows carry their group so the filter can hide them without re-rendering. */
export default function LostList({ lakes }: { lakes: LostLake[] }) {
  return (
    <>
      <div aria-hidden className={`${ROW} mt-6 hidden md:grid pb-2 border-b border-rule label text-missing`}>
        <span className="col-span-4">Lake</span>
        <span className="col-span-2 text-right">Acres</span>
        <span className="col-span-6">On the site now</span>
      </div>
      <ul className="mt-6 md:mt-0 border-t border-rule md:border-t-0">
        {lakes.map((lake) => (
          <li
            key={lake.id}
            data-cat={lake.occupied}
            className="border-b border-rule [content-visibility:auto] [contain-intrinsic-size:auto_50px]"
          >
            <Link
              href={`/lake/${lake.id}`}
              prefetch={false}
              className={`${ROW} grid group gap-y-1 py-3 hover:bg-well active:bg-rule`}
            >
              <span className="col-span-8 md:col-span-4 underline decoration-1 underline-offset-3 group-hover:decoration-2">
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
              <span className="col-span-12 md:col-span-6 label font-normal md:text-[17px] md:leading-[1.55]">
                <span className="sr-only">On the site now: </span>
                {lake.nowOccupiedBy ?? <span className="missing">Nothing on record</span>}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}
