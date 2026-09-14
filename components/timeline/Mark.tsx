import type { CSSProperties, KeyboardEvent, Ref } from "react";
import type { Placed } from "./layout";
import Piece from "./Piece";
import styles from "./timeline.module.css";
import { statusName } from "./words";

/** One record on the timeline. Only the current mark is in the tab order; the arrow keys move between the rest. */
export default function Mark({
  placed,
  rows,
  selected,
  tabbable,
  hovered,
  onSelect,
  onHover,
  onKeyDown,
  ref,
}: {
  placed: Placed;
  rows: number;
  selected: boolean;
  tabbable: boolean;
  /** The pointer is over it: show its name tag. Only this mark carries one, to keep the page light. */
  hovered: boolean;
  onSelect: (index: number) => void;
  onHover: (index: number | null) => void;
  onKeyDown: (event: KeyboardEvent<HTMLButtonElement>) => void;
  ref: Ref<HTMLButtonElement>;
}) {
  const { source } = placed;
  const style = {
    "--a": placed.a,
    "--len": placed.len,
    "--row": placed.row,
    "--rows": rows,
    "--step": placed.step,
  } as CSSProperties;

  return (
    <button
      ref={ref}
      type="button"
      className={styles.mark}
      style={style}
      data-side={source.from === undefined || placed.a > 0.6 ? "end" : "start"}
      aria-pressed={selected}
      aria-controls="timeline-slip"
      aria-label={`${source.when}. ${source.title}. ${statusName(source.status)}.`}
      tabIndex={tabbable ? 0 : -1}
      onFocus={() => onSelect(placed.index)}
      onClick={() => onSelect(placed.index)}
      onPointerEnter={(event) => event.pointerType === "mouse" && onHover(placed.index)}
      onPointerLeave={() => onHover(null)}
      onKeyDown={onKeyDown}
    >
      <Piece status={source.status} />
      {hovered && (
        <span aria-hidden className={`${styles.tag} label`}>
          <span className="text-missing">{source.when}</span> {source.title}
        </span>
      )}
    </button>
  );
}
