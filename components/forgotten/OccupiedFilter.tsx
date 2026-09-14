"use client";

import { useState, type ReactNode } from "react";
import { formatCount } from "@/lib/format";
import type { OccupiedCount } from "./lost";
import { OCCUPIED, type OccupiedId } from "./occupied";

/** The list is rendered on the server; picking a group only hides the other rows. */
const HIDE_OTHERS = OCCUPIED.map(({ id }) => `[data-show="${id}"] [data-cat]:not([data-cat="${id}"]){display:none}`).join("");

/**
 * What stands on the sites now, as one bar per group. Each bar is also the filter for the list below.
 * Returns two cells of the parent 12-column grid: the bars, then the list.
 */
export default function OccupiedFilter({
  counts,
  total,
  children,
}: {
  counts: OccupiedCount[];
  total: number;
  children: ReactNode;
}) {
  const [show, setShow] = useState<OccupiedId | null>(null);
  const max = Math.max(...counts.map((group) => group.count));
  const active = counts.find((group) => group.id === show);

  return (
    <>
      <style>{HIDE_OTHERS}</style>

      <ul className="col-span-12 lg:col-span-8 mt-10 lg:mt-0" aria-label="Show only the lakes whose site is now">
        {counts.map((group) => {
          const pressed = group.id === show;
          const quiet = show !== null && !pressed;
          return (
            <li key={group.id}>
              <button
                type="button"
                aria-pressed={pressed}
                onClick={() => setShow(pressed ? null : group.id)}
                className="-mx-2 block w-[calc(100%+16px)] px-2 py-2 text-left cursor-pointer hover:bg-well active:bg-rule"
              >
                <span className={`flex items-baseline justify-between gap-6 ${quiet ? "text-missing" : ""}`}>
                  <span className={group.id === "none" ? "italic" : pressed ? "font-medium" : ""}>{group.label}</span>
                  <span className="tabular-nums">{formatCount(group.count)}</span>
                </span>
                <span aria-hidden className="mt-2 block h-2">
                  <span
                    className={`block h-full ${quiet ? "bg-rule" : "bg-ink"}`}
                    style={{ width: `${(group.count / max) * 100}%` }}
                  />
                </span>
              </button>
            </li>
          );
        })}
      </ul>

      <div className="col-span-12 mt-16 md:mt-26">
        <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
          <h3 className="font-serif text-[26px] md:text-[36px] leading-none">Every lake that is gone</h3>
          {active && (
            <button type="button" onClick={() => setShow(null)} className="-my-3 py-3 ink-link cursor-pointer">
              Show all {formatCount(total)}
            </button>
          )}
        </div>
        <p aria-live="polite" className="mt-2 label font-normal text-missing">
          {active
            ? `Showing the ${formatCount(active.count)} lakes ${active.phrase}, largest first.`
            : `Showing all ${formatCount(total)}, largest first.`}
        </p>
        <div data-show={show ?? "all"}>{children}</div>
      </div>
    </>
  );
}
