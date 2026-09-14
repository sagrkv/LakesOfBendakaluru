import { paperFor } from "@/lib/valleys";

/** A scrap of the lake's paper: the same mark as the map. */
export default function Swatch({ valley, sheet }: { valley?: string; sheet?: string }) {
  return (
    <span
      aria-hidden
      className="inline-block size-3 shrink-0 border border-ink/60"
      style={{ backgroundColor: sheet ?? paperFor(valley).sheet }}
    />
  );
}
