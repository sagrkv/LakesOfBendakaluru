import { paperFor } from "@/lib/valleys";

/** A scrap of the lake's paper, or a hollow ring for a lake that has disappeared: the same marks as the map. */
export default function Swatch({ valley, gone = false, sheet }: { valley?: string; gone?: boolean; sheet?: string }) {
  if (gone) return <span aria-hidden className="inline-block size-3 shrink-0 rounded-full border-[1.5px] border-ink" />;
  return (
    <span
      aria-hidden
      className="inline-block size-3 shrink-0 border border-ink/60"
      style={{ backgroundColor: sheet ?? paperFor(valley).sheet }}
    />
  );
}
