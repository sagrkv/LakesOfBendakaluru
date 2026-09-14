import type { ReactNode } from "react";

/** The name of a mark, shown while the pointer is on it or a tap has focused it. Opens toward the middle of the line. */
export default function Tag({ end, children }: { end: boolean; children: ReactNode }) {
  return (
    <span
      className={`label pointer-events-none absolute bottom-full z-10 mb-2 hidden w-max max-w-[240px] bg-ink px-3 py-2 font-normal text-table group-hover:block group-focus:block ${
        end ? "right-0" : "left-0"
      }`}
    >
      {children}
    </span>
  );
}
