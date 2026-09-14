import type { LandCoverYear } from "@/lib/lake";
import { percent } from "../words";
import { fractionOf, placeIn, type Segment } from "./axis";
import Tag from "./Tag";
import { sharesOf } from "./water";

/** Bottom to top, the same order as the key. Water is ink like every other water mark on the page. */
const PARTS = [
  { key: "water", label: "water", fill: "bg-ink" },
  { key: "built", label: "built on or bare", fill: "bg-missing" },
  { key: "plants", label: "plants or weed", fill: "bg-rule" },
] as const;

/** What covered the lake's area each year, as one stacked column per year. */
export default function CoverLane({ rows, segments }: { rows: LandCoverYear[]; segments: Segment[] }) {
  return (
    <>
      <div className="label col-span-full mt-6 mb-2 flex flex-wrap items-center gap-x-4 gap-y-1 font-normal">
        <span>What covers it each year:</span>
        {PARTS.map((part) => (
          <span key={part.key} className="flex items-center gap-1.5">
            <span aria-hidden className={`size-2.5 shrink-0 ${part.fill}`} />
            {part.label}
          </span>
        ))}
      </div>
      <div className="col-span-full grid h-8 grid-cols-subgrid">
        {segments.map((segment) => (
          <div key={`${segment.kind}-${segment.from}`} className="relative min-w-0">
            {segment.kind === "years"
              ? rows
                  .filter((row) => row.year >= segment.from && row.year <= segment.to)
                  .map((row) => {
                    const shares = sharesOf(row);
                    const total = shares.water + shares.built + shares.plants || 1;
                    return (
                      <span
                        key={row.year}
                        tabIndex={-1}
                        className="group absolute inset-y-0 outline-none"
                        style={placeIn(segment, row.year)}
                      >
                        <span className="absolute inset-x-[12%] inset-y-0 flex flex-col-reverse group-hover:outline-2 group-hover:outline-offset-1 group-hover:outline-ink group-focus:outline-2 group-focus:outline-offset-1 group-focus:outline-ink">
                          {PARTS.map((part) => (
                            <span key={part.key} className={part.fill} style={{ height: `${(shares[part.key] / total) * 100}%` }} />
                          ))}
                        </span>
                        <Tag end={fractionOf(segments, row.year) > 0.5}>
                          <span className="tabular-nums">{row.year}</span>:{" "}
                          {PARTS.map((part) => `${percent(shares[part.key])} ${part.label}`).join(", ")}
                        </Tag>
                      </span>
                    );
                  })
              : null}
          </div>
        ))}
      </div>
    </>
  );
}
