import type { Tone } from "./types";

/** Paper pasted down when the record finds a lake; an outline only when it finds none. */
export const PIECE: Record<Tone, string> = {
  lake: "bg-ink shadow-[1px_2px_0_rgb(90_59_18/0.35)]",
  "no-lake": "bg-table shadow-[inset_0_0_0_1.5px_var(--color-ink)]",
};

export default function Piece({ tone, className = "" }: { tone: Tone; className?: string }) {
  return <span aria-hidden className={`block ${PIECE[tone]} ${className}`} />;
}
