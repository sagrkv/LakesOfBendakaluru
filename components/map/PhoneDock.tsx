import type { ReactNode } from "react";
import CollectionPicker from "./CollectionPicker";
import type { CollectionKey } from "./collections";

type Props = {
  stats: string | null;
  ready: boolean;
  onChoose: (key: CollectionKey) => void;
  /** The tapped lake's card; while it shows, the list below keeps its scroll position hidden. */
  card: ReactNode;
  /** The open collection's list, or nothing to show the collections. */
  list: ReactNode;
};

/** The phone layout: a dock under the map, so nothing covers the map's own controls. */
export default function PhoneDock({ stats, ready, onChoose, card, list }: Props) {
  return (
    <div className="relative z-10 flex max-h-[60dvh] flex-col border-t border-rule bg-table pr-[env(safe-area-inset-right)] pb-[max(12px,env(safe-area-inset-bottom))] pl-[env(safe-area-inset-left)] shadow-[0_-10px_18px_-8px_rgb(90_59_18/0.25)]">
      {card ? <div className="min-h-0 overflow-y-auto overscroll-contain">{card}</div> : null}
      <div hidden={Boolean(card)} className="flex min-h-0 flex-1 flex-col pt-2">
        {list ?? (
          <div className="px-4 pt-1">
            <p className={`label text-missing ${stats ? "" : "invisible"}`}>{stats ?? "Counting the lakes"}</p>
            <div className="mt-2">
              <CollectionPicker variant="strip" counts={null} disabled={!ready} onChoose={onChoose} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
