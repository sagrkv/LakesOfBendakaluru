import { useId } from "react";
import type { LakeSummary } from "@/lib/lake";
import { COLLECTIONS, type CollectionKey, type Ranked } from "./collections";
import NearMeState from "./NearMeState";
import Swatch from "./Swatch";
import type { NearMe } from "./useNearMe";
import { distanceText, valleyName } from "./words";

type Props = {
  collection: CollectionKey;
  rows: Ranked[] | null;
  loading: boolean;
  near: NearMe;
  onLocate: () => void;
  selectedId: string | null;
  onSelect: (lake: LakeSummary) => void;
  onBack: () => void;
  /** The phone dock: smaller header, and the list can fold away to give the map room. */
  compact?: boolean;
  collapsed?: boolean;
  onToggle?: () => void;
};

/** Beyond this, Near me is not near anything on record. */
const FAR_KM = 50;

function BackArrow() {
  return (
    <svg width="16" height="12" viewBox="0 0 16 12" aria-hidden>
      <path d="M6 1L1 6l5 5M1 6h14" fill="none" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

export default function RankedList(props: Props) {
  const { collection, rows, loading, near, compact = false, collapsed = false } = props;
  const info = COLLECTIONS[collection];
  const headingId = useId();
  const edge = compact ? "px-4" : "px-6";
  const note = rows?.length ? info.note(rows.length) : null;
  const nearestKm = collection === "near" ? rows?.[0]?.km : undefined;

  const header = compact ? (
    <header className={`${edge} pt-1 pb-3`}>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={props.onBack}
          aria-label="All collections"
          className="-ml-3 grid size-11 shrink-0 place-items-center transition-colors duration-150 hover:bg-well active:bg-rule"
        >
          <BackArrow />
        </button>
        <h2 id={headingId} className="min-w-0 flex-1 font-serif text-[26px] leading-none">
          {info.title}
        </h2>
        <button
          type="button"
          onClick={props.onToggle}
          aria-expanded={!collapsed}
          className="label ink-link -mr-2 h-11 shrink-0 px-2"
        >
          {collapsed ? "Show list" : "Hide list"}
        </button>
      </div>
      {!collapsed && note ? <p className="label mt-1 text-missing">{note}</p> : null}
    </header>
  ) : (
    <header className={`${edge} pb-4`}>
      <button
        type="button"
        onClick={props.onBack}
        className="label -ml-2 inline-flex h-11 items-center gap-2 px-2 transition-colors duration-150 hover:bg-well active:bg-rule"
      >
        <BackArrow />
        All collections
      </button>
      <h2 id={headingId} className="mt-1 font-serif text-[36px] leading-[0.95]">
        {info.title}
      </h2>
      {note ? <p className="label mt-2 text-missing">{note}</p> : null}
    </header>
  );

  let body;
  if (loading) {
    body = (
      <p role="status" className={`${edge} label py-6 text-missing`}>
        Laying out the lakes…
      </p>
    );
  } else if (rows === null) {
    body = <NearMeState state={near} onLocate={props.onLocate} edge={edge} />;
  } else if (rows.length === 0) {
    body = <p className={`${edge} py-6 text-[17px]`}>{info.empty}</p>;
  } else {
    body = (
      <>
        {nearestKm !== undefined && nearestKm > FAR_KM ? (
          <p className={`${edge} pb-4 text-[17px]`}>
            The nearest lake on record is {distanceText(nearestKm)} away. Near me works in and around Bengaluru.
          </p>
        ) : null}
        <ol aria-labelledby={headingId} className="border-t border-rule">
          {rows.map(({ lake, value, detail }, i) => (
            <li key={lake.id} className="border-b border-rule [contain-intrinsic-size:auto_72px] [content-visibility:auto]">
              <button
                type="button"
                onClick={() => props.onSelect(lake)}
                aria-current={lake.id === props.selectedId ? "true" : undefined}
                className={`grid w-full grid-cols-[24px_minmax(0,1fr)_auto] items-baseline gap-x-3 ${edge} py-3 text-left transition-colors duration-150 hover:bg-well focus-visible:bg-well focus-visible:outline-offset-[-2px] active:bg-rule aria-[current=true]:bg-well aria-[current=true]:shadow-[inset_3px_0_0_var(--color-ink)]`}
              >
                <span className="label text-missing tabular-nums">{i + 1}</span>
                <span className="min-w-0">
                  <span className="block font-serif text-[26px] leading-none break-words">{lake.name}</span>
                  <span className="label mt-1 flex items-center gap-2 text-missing">
                    <Swatch valley={lake.valley} />
                    <span className="min-w-0">{detail ?? valleyName(lake.valley) ?? "No valley on record"}</span>
                  </span>
                </span>
                <span className="label text-right tabular-nums">
                  {value ?? <span className="missing">Size not on record</span>}
                </span>
              </button>
            </li>
          ))}
        </ol>
      </>
    );
  }

  return (
    <section aria-labelledby={headingId} className="flex min-h-0 flex-1 flex-col">
      {header}
      {collapsed ? null : <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">{body}</div>}
    </section>
  );
}
