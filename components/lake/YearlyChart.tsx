import { formatAcres } from "@/lib/format";

type Year = { year: number; waterAcres: number; observedAcres: number };

const PLOT_H = 200;

function niceCeil(v: number): number {
  if (v <= 0) return 1;
  const p = 10 ** Math.floor(Math.log10(v));
  return ([1, 2, 2.5, 5, 10].find((m) => m * p >= v) ?? 10) * p;
}

/**
 * Acres of water each year, one ink line on the table. Years the satellite saw less than half
 * the lake break the line and show as hollow dots, because their low numbers are not real.
 * Hover or tap a year for its reading; the same numbers are stated beside the chart.
 */
export default function YearlyChart({ years, outlineAcres }: { years: Year[]; outlineAcres?: number }) {
  const first = years[0].year;
  const last = years[years.length - 1].year;
  const span = Math.max(last - first, 1);
  const maxObserved = Math.max(...years.map((d) => d.observedAcres));
  const top = niceCeil(Math.max(...years.map((d) => d.waterAcres), outlineAcres ?? 0) * 1.1);
  const x = (year: number) => ((year - first) / span) * 100;
  const y = (acres: number) => 100 - (acres / top) * 100;
  const poor = (d: Year) => d.observedAcres < maxObserved * 0.5;

  const runs: Year[][] = [];
  for (const d of years) {
    const run = runs[runs.length - 1];
    const prev = run?.[run.length - 1];
    if (poor(d)) continue;
    if (prev && d.year === prev.year + 1) run.push(d);
    else runs.push([d]);
  }
  const pt = (d: Year) => `${x(d.year) * 10},${(y(d.waterAcres) / 100) * PLOT_H}`;
  const ticks = [first, ...[1990, 2000, 2010].filter((t) => t > first + 3 && t < last - 3), last];
  const hasPoor = years.some(poor);
  const colW = 100 / years.length;

  return (
    <figure className="pt-6">
      <div className="relative mx-1" style={{ height: PLOT_H }}>
        <span className="label absolute -top-6 left-0 font-normal tabular-nums">
          {top.toLocaleString("en-IN")} acres
        </span>
        <div className="absolute inset-x-0 top-0 border-t border-rule" />
        <div className="absolute inset-x-0 top-1/2 border-t border-rule" />
        <div className="absolute inset-x-0 bottom-0 border-t border-ink/40" />
        {outlineAcres !== undefined ? (
          <div className="absolute inset-x-0 border-t border-ink/40" style={{ top: `${y(outlineAcres)}%` }} />
        ) : null}

        <svg
          viewBox={`0 0 1000 ${PLOT_H}`}
          preserveAspectRatio="none"
          aria-hidden
          className="absolute inset-0 size-full overflow-visible"
        >
          {runs.map((run) => (
            <g key={run[0].year}>
              {run.length > 1 ? (
                <polygon
                  points={`${x(run[0].year) * 10},${PLOT_H} ${run.map(pt).join(" ")} ${x(run[run.length - 1].year) * 10},${PLOT_H}`}
                  className="fill-ink/8"
                />
              ) : null}
              <polyline
                points={run.length > 1 ? run.map(pt).join(" ") : `${pt(run[0])} ${pt(run[0])}`}
                fill="none"
                strokeWidth={run.length > 1 ? 2 : 6}
                strokeLinejoin="round"
                strokeLinecap="round"
                vectorEffect="non-scaling-stroke"
                className="stroke-ink"
              />
            </g>
          ))}
        </svg>

        {years.filter(poor).map((d) => (
          <span
            key={d.year}
            aria-hidden
            className="absolute size-2 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-missing bg-table"
            style={{ left: `${x(d.year)}%`, top: `${y(d.waterAcres)}%` }}
          />
        ))}

        {years.map((d) => (
          <div
            key={d.year}
            tabIndex={-1}
            aria-hidden
            className="group absolute inset-y-0 outline-none"
            style={{ left: `${x(d.year) - colW / 2}%`, width: `${colW}%` }}
          >
            <span className="absolute inset-y-0 left-1/2 hidden w-px bg-ink/40 group-hover:block group-focus:block" />
            <span
              className={`label absolute bottom-full z-10 mb-2 hidden w-max max-w-[220px] bg-ink px-2.5 py-1.5 font-normal text-table group-hover:block group-focus:block ${
                x(d.year) > 50 ? "right-1/2" : "left-1/2"
              }`}
            >
              <span className="font-medium">
                {d.year}: {formatAcres(d.waterAcres)} acres of water
              </span>
              {poor(d) ? (
                <span className="block">The satellite saw {Math.round((d.observedAcres / maxObserved) * 100)}% of the lake</span>
              ) : null}
            </span>
          </div>
        ))}
      </div>

      <div className="relative mx-1 mt-2 h-5" aria-hidden>
        {ticks.map((t, i) => (
          <span
            key={t}
            className={`label absolute top-0 font-normal tabular-nums ${
              i === 0 ? "" : i === ticks.length - 1 ? "-translate-x-full" : "-translate-x-1/2"
            }`}
            style={{ left: `${x(t)}%` }}
          >
            {t}
          </span>
        ))}
      </div>

      <figcaption className="label mt-3 font-normal">
        <span className="sr-only">
          Between {formatAcres(Math.min(...years.map((d) => d.waterAcres)))} and{" "}
          {formatAcres(Math.max(...years.map((d) => d.waterAcres)))} acres of water each year from {first} to {last}.{" "}
        </span>
        The thick line is water each year.
        {outlineAcres !== undefined ? ` The thin line is the drawn outline, ${formatAcres(outlineAcres)} acres.` : ""}
        {hasPoor ? " Hollow dots are years the satellite saw less than half the lake." : ""}
      </figcaption>
    </figure>
  );
}
