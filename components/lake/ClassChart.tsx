import type { WaterClass, WaterReading } from "@/lib/lake";
import { formatMonth, WATER_CLASS } from "@/lib/format";

const CLASSES: WaterClass[] = ["A", "B", "C", "D", "E"];
const ROW_H = 48;
/** The dot line sits low in each row, leaving the top for the row's words. */
const DOT_Y = 36;

const monthNumber = (month: string) => {
  const [y, m] = month.split("-").map(Number);
  return y * 12 + (m - 1);
};

/**
 * The state board's class for each tested month, one row per class from cleanest to dirtiest.
 * Consecutive months are joined; untested months leave a gap. Hover or tap a month for its reading.
 */
export default function ClassChart({ readings, start, end }: { readings: WaterReading[]; start: string; end: string }) {
  const s = monthNumber(start);
  const span = Math.max(monthNumber(end) - s, 1);
  const x = (month: string) => ((monthNumber(month) - s) / span) * 100;
  const yPx = (c: WaterClass) => CLASSES.indexOf(c) * ROW_H + DOT_Y;
  const height = CLASSES.length * ROW_H;
  const classed = readings
    .filter((r): r is WaterReading & { class: WaterClass } => Boolean(r.class))
    .sort((a, b) => monthNumber(a.month) - monthNumber(b.month));

  const segments: [WaterReading & { class: WaterClass }, WaterReading & { class: WaterClass }][] = [];
  for (let i = 1; i < classed.length; i++) {
    if (monthNumber(classed[i].month) - monthNumber(classed[i - 1].month) === 1) {
      segments.push([classed[i - 1], classed[i]]);
    }
  }

  const years: { label: string; at: number }[] = [];
  const firstYear = Number(start.slice(0, 4));
  const lastYear = Number(end.slice(0, 4));
  for (let year = firstYear + 1; year <= lastYear; year++) {
    years.push({ label: String(year), at: x(`${year}-01`) });
  }
  if (!years.length || years[0].at > 16) years.unshift({ label: String(firstYear), at: 0 });
  const colW = 100 / (span + 1);

  return (
    <figure className="pt-2">
      <figcaption className="sr-only">
        {CLASSES.map((c) => {
          const n = classed.filter((r) => r.class === c).length;
          return n ? `${WATER_CLASS[c].short}: ${n} months. ` : "";
        }).join("")}
        Every month is listed in the readings below.
      </figcaption>
      <div className="relative mx-1" style={{ height }}>
        {CLASSES.map((c, i) => (
          <div key={c} className="absolute inset-x-0" style={{ top: i * ROW_H }}>
            <span className="label absolute top-1 left-0 font-normal">{WATER_CLASS[c].short}</span>
            <div className="absolute inset-x-0 border-t border-rule" style={{ top: DOT_Y }} />
          </div>
        ))}

        <svg
          viewBox={`0 0 1000 ${height}`}
          preserveAspectRatio="none"
          aria-hidden
          className="absolute inset-0 size-full overflow-visible"
        >
          {segments.map(([a, b]) => (
            <line
              key={a.month}
              x1={x(a.month) * 10}
              y1={yPx(a.class)}
              x2={x(b.month) * 10}
              y2={yPx(b.class)}
              strokeWidth={2}
              vectorEffect="non-scaling-stroke"
              className="stroke-ink/40"
            />
          ))}
        </svg>

        {classed.map((r) => (
          <span
            key={r.month}
            aria-hidden
            className="absolute size-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-table bg-ink"
            style={{ left: `${x(r.month)}%`, top: yPx(r.class) }}
          />
        ))}

        {classed.map((r) => (
          <div
            key={r.month}
            tabIndex={-1}
            aria-hidden
            className="group absolute inset-y-0 outline-none"
            style={{ left: `${x(r.month) - colW / 2}%`, width: `${colW}%` }}
          >
            <span className="absolute inset-y-0 left-1/2 hidden w-px bg-ink/40 group-hover:block group-focus:block" />
            <span
              className={`label absolute bottom-full z-10 mb-2 hidden w-max max-w-[220px] bg-ink px-2.5 py-1.5 font-normal text-table group-hover:block group-focus:block ${
                x(r.month) > 50 ? "right-1/2" : "left-1/2"
              }`}
            >
              <span className="block font-medium">{formatMonth(r.month)}</span>
              {WATER_CLASS[r.class].long}
            </span>
          </div>
        ))}
      </div>

      <div className="relative mx-1 mt-2 h-5" aria-hidden>
        {years.map((year) => (
          <span
            key={year.label}
            className={`label absolute top-0 font-normal tabular-nums ${year.at > 92 ? "-translate-x-full" : ""}`}
            style={{ left: `${year.at}%` }}
          >
            {year.label}
          </span>
        ))}
      </div>
    </figure>
  );
}
