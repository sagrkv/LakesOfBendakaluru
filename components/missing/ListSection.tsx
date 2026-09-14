import { formatCount } from "@/lib/format";
import { describe, isFiltered, type Filter, type Tagged } from "./filter";
import MissingRow, { ROW } from "./MissingRow";
import type { AllMissing } from "./useAllMissing";

/**
 * Every missing lake, largest first. The largest few arrive with the page; the rest load when
 * someone asks to see them all or presses a bar.
 */
export default function ListSection({
  filter,
  top,
  all,
  rows,
  total,
  printed,
  onLoad,
  onClear,
}: {
  filter: Filter;
  top: Tagged[];
  all: AllMissing;
  /** The lakes that match, once the full list is here; null before. */
  rows: Tagged[] | null;
  total: number;
  printed: Record<string, number[]>;
  onLoad: () => void;
  onClear: () => void;
}) {
  const filtered = isFiltered(filter);
  const shown = rows ?? (filtered ? [] : top);
  const partial = rows === null && !filtered && top.length < total;

  const status =
    all.status === "error"
      ? null
      : rows === null
        ? filtered
          ? "Finding the lakes that match."
          : partial
            ? `Showing the ${formatCount(top.length)} largest of ${formatCount(total)}.`
            : `Showing all ${formatCount(total)}, largest first.`
        : filtered
          ? rows.length
            ? `Showing ${describe(filter, rows.length)}, largest first.`
            : null
          : `Showing all ${formatCount(total)}, largest first.`;

  return (
    <section id="list" aria-labelledby="list-title" className="page-x pb-16 md:pb-26 scroll-mt-6">
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
        <h2 id="list-title" className="font-serif text-[26px] md:text-[36px] leading-none">
          <span className="highlight">Every missing lake</span>
        </h2>
        {filtered && (
          <button type="button" onClick={onClear} className="-my-3 py-3 ink-link cursor-pointer">
            Clear choices
          </button>
        )}
      </div>
      <p aria-live="polite" className="mt-2 label font-normal text-missing">
        {status}
      </p>

      {shown.length > 0 && (
        <>
          <div aria-hidden className={`${ROW} mt-6 hidden md:grid pb-2 border-b border-rule label text-missing`}>
            <span className="col-span-3">Lake</span>
            <span className="col-span-2 text-right">Acres in 2018</span>
            <span className="col-span-3">Where</span>
            <span className="col-span-4">What the record says</span>
          </div>
          <ul className="mt-6 md:mt-0 border-t border-rule md:border-t-0">
            {shown.map((lake) => (
              <MissingRow key={lake.id} lake={lake} printed={printed[lake.id]} />
            ))}
          </ul>
        </>
      )}

      {rows !== null && filtered && rows.length === 0 && (
        <div className="mt-6">
          <p className="missing">No lake matches all of these choices. Let go of one of the bars above, or list them all.</p>
          <button type="button" onClick={onClear} className="-mb-3 py-3 ink-link cursor-pointer">
            Show all {formatCount(total)}
          </button>
        </div>
      )}

      {all.status === "error" && (
        <div role="alert" className="mt-6">
          <p>The list did not load. Check your connection, then try again.</p>
          <button type="button" onClick={onLoad} className="-mb-3 py-3 ink-link cursor-pointer">
            Try again
          </button>
        </div>
      )}

      {partial && all.status !== "error" && (
        <button
          type="button"
          onClick={onLoad}
          disabled={all.status === "loading"}
          aria-busy={all.status === "loading"}
          className="button-ink mt-10 text-[28px] md:text-[38px] cursor-pointer disabled:cursor-progress disabled:opacity-70 disabled:translate-none disabled:shadow-[2px_4px_0_rgb(90_59_18/0.35)]"
        >
          {all.status === "loading" ? "Loading the list" : `Show all ${formatCount(total)} lakes`}
        </button>
      )}
    </section>
  );
}
