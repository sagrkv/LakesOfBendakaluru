import type { Segment } from "./axis";

const DECADES = [1900, 1910, 1920, 1930, 1940, 1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020];

/**
 * The axis: a solid line under years with records, a dashed one where the record breaks.
 * Each column labels its own first and last year, and decades once there is room, measured per column.
 */
export default function Ticks({ segments }: { segments: Segment[] }) {
  return (
    <div className="col-span-full mt-2 grid grid-cols-subgrid">
      {segments.map((segment, i) => {
        const key = `${segment.kind}-${segment.from}`;
        const tick = "label absolute top-1 font-normal tabular-nums";
        if (segment.kind === "gap") {
          return (
            <div key={key} className="relative h-6 border-t border-dashed border-missing">
              {i === segments.length - 1 ? <span className={`${tick} right-0`}>{segment.to}</span> : null}
            </div>
          );
        }
        const units = segment.to - segment.from + 1;
        if (units === 1) {
          return (
            <div key={key} className="relative h-6 border-t border-ink">
              <span className={`${tick} inset-x-0 text-center`}>{segment.from}</span>
            </div>
          );
        }
        const decades = DECADES.filter((d) => d - segment.from >= 5 && segment.to - d >= 5);
        return (
          <div key={key} className="@container relative h-6 border-t border-ink">
            <span className={`${tick} left-0`}>{segment.from}</span>
            <span className={`${tick} right-0 hidden @min-[96px]:block`}>{segment.to}</span>
            {decades.map((d) => (
              <span
                key={d}
                className={`${tick} hidden -translate-x-1/2 @min-[480px]:block`}
                style={{ left: `${((d - segment.from + 0.5) / units) * 100}%` }}
              >
                {d}
              </span>
            ))}
          </div>
        );
      })}
    </div>
  );
}
