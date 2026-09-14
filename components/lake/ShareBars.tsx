import { monthOf, percent, sentence } from "./words";

type Share = { season: string; from: string; to: string; openWaterPct: number; weedCoverPct: number; dryOrBuiltPct: number };

const PARTS = [
  { key: "openWaterPct", label: "open water", fill: "bg-ink" },
  { key: "weedCoverPct", label: "floating weed", fill: "bg-missing" },
  { key: "dryOrBuiltPct", label: "dry or built", fill: "bg-rule" },
] as const;

/** What covers the lake in each recent season, as one bar split three ways, every share written out. */
export default function ShareBars({ seasons }: { seasons: Share[] }) {
  return (
    <div className="grid gap-6 md:grid-cols-2">
      {seasons.map((season) => (
        <div key={season.from} className="min-w-0">
          <p className="label">
            {sentence(season.season)}, {monthOf(season.from)} to {monthOf(season.to)}
          </p>
          <div className="mt-2 flex h-3 gap-0.5" aria-hidden>
            {PARTS.filter((part) => season[part.key] > 0).map((part) => (
              <div key={part.key} className={part.fill} style={{ flexGrow: season[part.key], flexBasis: 0 }} />
            ))}
          </div>
          <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
            {PARTS.map((part) => (
              <li key={part.key} className="label flex items-center gap-1.5 font-normal">
                <span aria-hidden className={`size-2.5 shrink-0 ${part.fill}`} />
                {percent(season[part.key])} {part.label}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
