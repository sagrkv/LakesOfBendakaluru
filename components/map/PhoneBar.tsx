"use client";

import { useState } from "react";
import MadeBy from "@/components/MadeBy";
import Wordmark from "@/components/Wordmark";
import type { LakeSummary } from "@/lib/lake";
import Legend from "./Legend";
import SearchBox from "./SearchBox";
import type { SearchIndex } from "./search";

/** The top of the map on a phone: wordmark and search on one slip, the map key under it. */
export default function PhoneBar({
  index,
  failed,
  onPick,
}: {
  index: SearchIndex | null;
  failed: boolean;
  onPick: (lake: LakeSummary) => void;
}) {
  const [keyOpen, setKeyOpen] = useState(false);

  return (
    <div className="pointer-events-none absolute inset-x-0 top-0 z-20 pt-[max(12px,env(safe-area-inset-top))] pr-[max(16px,env(safe-area-inset-right))] pl-[max(16px,env(safe-area-inset-left))]">
      <div className="group slip pointer-events-auto flex items-center gap-3 py-2 pr-2 pl-4">
        {/* The wordmark steps aside while someone is searching, so the field gets the whole slip. */}
        <Wordmark
          href="/"
          className="[--tilt:0deg] shadow-none! group-has-[[data-search]:focus-within]:hidden group-has-[input:not(:placeholder-shown)]:hidden"
        />
        <SearchBox index={index} failed={failed} compact onPick={onPick} />
      </div>

      <div className="mt-3 flex flex-col items-end">
        <button
          type="button"
          aria-expanded={keyOpen}
          aria-controls="map-key"
          onClick={() => setKeyOpen((open) => !open)}
          className="slip label pointer-events-auto h-11 px-3 transition-colors duration-150 hover:bg-well active:translate-y-px"
        >
          {keyOpen ? "Hide key" : "Map key"}
        </button>
        {keyOpen ? (
          <div id="map-key" className="slip pointer-events-auto mt-2 w-full max-w-[320px] p-4">
            <Legend columns={1} />
            <MadeBy className="mt-3 border-t border-rule pt-3" />
          </div>
        ) : null}
      </div>
    </div>
  );
}
