import { fractionOf, placeIn, stackRows, yearsOf, type Segment } from "./axis";
import Piece from "./Piece";
import Tag from "./Tag";
import type { Entry } from "./types";

const ROW = 20;

/** The dated records as paper pieces: a narrow piece for one year, a strip for a span. */
export default function RecordsLane({ entries, segments }: { entries: Entry[]; segments: Segment[] }) {
  const { rows, count } = stackRows(entries, segments);

  return (
    <div className="col-span-full grid grid-cols-subgrid" style={{ height: count * ROW }}>
      {segments.map((segment) => (
        <div key={`${segment.kind}-${segment.from}`} className="relative min-w-0">
          {segment.kind === "years"
            ? entries.flatMap((entry) => {
                const inside = yearsOf(entry).filter((year) => year >= segment.from && year <= segment.to);
                if (!inside.length) return [];
                const span = !entry.points && entry.to !== undefined && entry.to > entry.from;
                const runs = span ? [[inside[0], inside[inside.length - 1]]] : inside.map((year) => [year, year]);
                return runs.map(([from, to]) => (
                  <span
                    key={`${entry.id}-${from}`}
                    tabIndex={-1}
                    className="group absolute flex h-5 justify-center outline-none"
                    style={{ ...placeIn(segment, from, to), top: (rows.get(entry.id) ?? 0) * ROW }}
                  >
                    <Piece
                      tone={entry.tone}
                      className={`${span ? "absolute inset-x-px top-[3px]" : "mt-[3px] w-1.5 shrink-0"} h-3.5 transition-[translate] duration-150 group-hover:-translate-y-px group-focus:outline-2 group-focus:outline-offset-2 group-focus:outline-ink group-active:translate-y-px`}
                    />
                    <Tag end={fractionOf(segments, from) > 0.5}>
                      <span className="tabular-nums">{entry.when}</span>. {entry.label}
                    </Tag>
                  </span>
                ));
              })
            : null}
        </div>
      ))}
    </div>
  );
}
