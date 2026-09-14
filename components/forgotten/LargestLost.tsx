import Link from "next/link";
import { formatAcres, pitches } from "@/lib/format";
import type { LostLake } from "./lost";

/** The biggest lakes that are gone, largest first, with what stands on each now. */
export default function LargestLost({ lakes }: { lakes: LostLake[] }) {
  return (
    <section className="page-x py-16 md:py-26">
      <div className="grid grid-cols-12 gap-x-6">
        <h2 className="col-span-12 lg:col-span-4 font-serif text-[48px] md:text-[64px] leading-[0.95] text-balance">
          The largest lakes that are gone
        </h2>
        <ol className="col-span-12 lg:col-span-8 mt-10 lg:mt-0 grid sm:grid-cols-2 gap-x-6 gap-y-10">
          {lakes.map((lake) => (
            <li key={lake.id}>
              <Link href={`/lake/${lake.id}`} className="font-serif text-[26px] md:text-[36px] leading-none ink-link">
                {lake.name}
              </Link>
              <p className="mt-2 label">
                {formatAcres(lake.acres!)} acres, {pitches(lake.acres!)}
              </p>
              <p className="mt-3 label text-missing">On the site now</p>
              {lake.nowOccupiedBy ? <p>{lake.nowOccupiedBy}</p> : <p className="missing">Nothing on record</p>}
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
