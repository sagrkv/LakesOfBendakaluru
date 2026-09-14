import { formatCount } from "@/lib/format";
import { COLLECTION_KEYS, COLLECTIONS, type CollectionKey } from "./collections";

type Props = {
  counts: Partial<Record<CollectionKey, number>> | null;
  /** True until the lake list has loaded. */
  disabled: boolean;
  onChoose: (key: CollectionKey) => void;
  /** Rows in the laptop panel, a scrolling strip in the phone dock. */
  variant: "rows" | "strip";
};

export default function CollectionPicker({ counts, disabled, onChoose, variant }: Props) {
  if (variant === "strip") {
    return (
      <nav aria-label="Collections" className="-mx-4 overflow-x-auto overscroll-x-contain [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <ul className="flex w-max gap-2 px-4">
          {COLLECTION_KEYS.map((key) => (
            <li key={key}>
              <button
                type="button"
                disabled={disabled}
                onClick={() => onChoose(key)}
                className="h-11 bg-well px-3 text-[17px] leading-none whitespace-nowrap transition-colors duration-150 hover:bg-rule active:translate-y-px active:bg-rule disabled:cursor-wait disabled:text-missing"
              >
                {COLLECTIONS[key].title}
              </button>
            </li>
          ))}
        </ul>
      </nav>
    );
  }

  return (
    <nav aria-label="Collections">
      <h2 className="label px-6 pb-2 text-missing">Collections</h2>
      <ul className="border-t border-rule">
        {COLLECTION_KEYS.map((key) => {
          const count = counts?.[key];
          return (
            <li key={key} className="border-b border-rule">
              <button
                type="button"
                disabled={disabled}
                onClick={() => onChoose(key)}
                className="flex min-h-14 w-full items-baseline justify-between gap-4 px-6 py-3 text-left transition-colors duration-150 hover:bg-well focus-visible:bg-well focus-visible:outline-offset-[-2px] active:bg-rule disabled:cursor-wait disabled:text-missing disabled:hover:bg-transparent"
              >
                <span className="font-serif text-[26px] leading-none">{COLLECTIONS[key].title}</span>
                <span className="label shrink-0 text-missing tabular-nums">
                  {key === "near" ? "Uses your location" : count === undefined ? "" : formatCount(count)}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
