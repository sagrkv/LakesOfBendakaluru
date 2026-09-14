import { describe, isFiltered, type Filter } from "./filter";

/**
 * Under the bars, once a bar is pressed: how many lakes match and a jump to them,
 * so a choice made far above the list is answered where it was made.
 */
export default function MatchLine({ filter, count, failed }: { filter: Filter; count: number | null; failed: boolean }) {
  if (!isFiltered(filter)) return null;
  return (
    <p aria-live="polite" className="sm:col-span-2">
      {failed ? (
        <a href="#list" className="ink-link">
          The list did not load. Try again below
        </a>
      ) : count === null ? (
        <span className="text-missing">Finding the lakes</span>
      ) : count === 0 ? (
        <span className="missing">No lake matches all of these choices.</span>
      ) : (
        <a href="#list" className="ink-link">
          See {describe(filter, count)}
        </a>
      )}
    </p>
  );
}
