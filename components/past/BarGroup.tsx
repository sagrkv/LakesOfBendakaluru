import { formatCount } from "@/lib/format";

export type Bar = { id: string; label: string; count: number; missing?: boolean };

/**
 * A titled set of bars on one shared scale. Each bar is also a filter for the list:
 * press it to list only those lakes, press it again to let go.
 */
export default function BarGroup({
  title,
  bars,
  max,
  picked,
  onPick,
  showTotal = true,
}: {
  title: string;
  bars: Bar[];
  max: number;
  picked: string | null;
  onPick: (id: string | null) => void;
  /** Off when a lake can sit in more than one bar, so the sum would mislead. */
  showTotal?: boolean;
}) {
  if (!bars.length) return null;
  const total = bars.reduce((sum, bar) => sum + bar.count, 0);

  return (
    <div>
      <div className="flex items-baseline justify-between gap-6 pb-2 border-b border-rule label text-missing">
        <h3>{title}</h3>
        {showTotal && <span className="tabular-nums">{formatCount(total)}</span>}
      </div>
      <ul aria-label={title}>
        {bars.map((bar) => {
          const pressed = bar.id === picked;
          const quiet = picked !== null && !pressed;
          return (
            <li key={bar.id}>
              <button
                type="button"
                aria-pressed={pressed}
                onClick={() => onPick(pressed ? null : bar.id)}
                className="-mx-2 block w-[calc(100%+16px)] px-2 py-2 text-left cursor-pointer hover:bg-well active:bg-rule"
              >
                <span className={`flex items-baseline justify-between gap-6 ${quiet ? "text-missing" : ""}`}>
                  <span className={bar.missing ? "italic" : pressed ? "font-medium" : ""}>{bar.label}</span>
                  <span className="tabular-nums">{formatCount(bar.count)}</span>
                </span>
                <span aria-hidden className="mt-2 block h-2">
                  <span
                    className={`block h-full min-w-0.5 ${quiet ? "bg-rule" : "bg-ink"}`}
                    style={{ width: `${(bar.count / max) * 100}%` }}
                  />
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
