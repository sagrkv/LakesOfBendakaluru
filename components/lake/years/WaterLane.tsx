import type { LakeRecord } from "@/lib/lake";
import { formatAcres } from "@/lib/format";
import { fractionOf, placeIn, type Segment } from "./axis";
import Tag from "./Tag";
import { maxObservedOf, poorYear } from "./water";

type Year = NonNullable<NonNullable<LakeRecord["water"]>["yearly"]>[number];

/** Acres of open water each year as thin ink bars on one baseline. Grey bars are years the satellite saw too little. */
export default function WaterLane({ years, segments }: { years: Year[]; segments: Segment[] }) {
  const maxObserved = maxObservedOf(years);
  const top = Math.max(0, ...years.map((y) => y.waterAcres));
  const hasPoor = years.some((y) => poorYear(y, maxObserved));
  const first = years[0].year;
  const last = years[years.length - 1].year;

  return (
    <>
      <p className="label col-span-full mt-6 mb-2 font-normal">
        {top > 0 ? `Water seen by satellite each year, up to ${formatAcres(top)} acres` : `No open water seen by satellite, ${first}-${last}`}
        {hasPoor ? <span className="text-missing">. Grey: years it saw under half the lake</span> : null}
      </p>
      <div className="col-span-full grid h-10 grid-cols-subgrid">
        {segments.map((segment) => {
          const inside = segment.kind === "years" ? years.filter((y) => y.year >= segment.from && y.year <= segment.to) : [];
          return (
            <div key={`${segment.kind}-${segment.from}`} className="relative min-w-0">
              {inside.length ? (
                <span
                  aria-hidden
                  className="absolute bottom-0 h-px bg-ink/40"
                  style={placeIn(segment, inside[0].year, inside[inside.length - 1].year)}
                />
              ) : null}
              {inside.map((y) => {
                const poor = poorYear(y, maxObserved);
                return (
                  <span
                    key={y.year}
                    tabIndex={-1}
                    className="group absolute inset-y-0 outline-none hover:bg-well focus:bg-well"
                    style={placeIn(segment, y.year)}
                  >
                    {y.waterAcres > 0 ? (
                      <span
                        className={`absolute inset-x-[12%] bottom-0 ${poor ? "bg-missing" : "bg-ink"}`}
                        style={{ height: `max(2px, ${(y.waterAcres / top) * 100}%)` }}
                      />
                    ) : null}
                    <Tag end={fractionOf(segments, y.year) > 0.5}>
                      <span className="tabular-nums">{y.year}</span>: {formatAcres(y.waterAcres)} acres of water
                      {poor ? `. The satellite saw ${Math.round((y.observedAcres / maxObserved) * 100)}% of the lake` : ""}
                    </Tag>
                  </span>
                );
              })}
            </div>
          );
        })}
      </div>
    </>
  );
}
