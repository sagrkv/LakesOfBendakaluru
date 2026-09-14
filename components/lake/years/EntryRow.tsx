import SourceLink from "@/components/paper/SourceLink";
import ShareBars from "../ShareBars";
import RauQuotes from "./RauQuotes";
import type { Entry } from "./types";

/** One dated fact: the year, what the record says, and where it comes from. */
export default function EntryRow({ entry }: { entry: Entry }) {
  return (
    <li className="grid grid-cols-12 gap-x-6 gap-y-2 border-b border-rule py-4 md:py-6">
      <p className="col-span-12 font-serif text-[26px] leading-none tabular-nums md:col-span-3 md:text-[36px] xl:col-span-2">
        {entry.when}
      </p>
      <div className="col-span-12 min-w-0 md:col-span-9 xl:col-span-7">
        <p className="max-w-[65ch]">{entry.label}</p>
        {entry.notes.map((note) => (
          <p key={note} className="label mt-1 max-w-[65ch] font-normal">
            {note}
          </p>
        ))}
        {entry.seasons ? (
          <div className="mt-4">
            <ShareBars seasons={entry.seasons} />
          </div>
        ) : null}
        {entry.rau ? <RauQuotes rau={entry.rau} /> : null}
      </div>
      {entry.link || entry.sources.length ? (
        <div className="col-span-12 flex flex-wrap items-baseline gap-x-4 gap-y-1 md:col-span-9 md:col-start-4 xl:col-span-3 xl:col-start-auto">
          {entry.link ? (
            <a href={entry.link.href} className="label ink-link">
              {entry.link.label}
            </a>
          ) : null}
          {entry.sources.map((source) => (
            <SourceLink key={source.key} source={source} />
          ))}
        </div>
      ) : null}
    </li>
  );
}
